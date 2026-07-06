package com.example.taskdesk.dao;

import com.example.taskdesk.model.TaskAuditEntry;
import com.example.taskdesk.util.DateUtils;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.Date;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class AuditDAO {
    private final JdbcConnectionManager connectionManager = JdbcConnectionManager.getInstance();

    public void insertAuditEntry(TaskAuditEntry entry) {
        String sql = "INSERT INTO TASK_AUDIT (TASK_ID, ACTION, OLD_VALUE, NEW_VALUE, PERFORMED_BY_USER_ID, PERFORMED_AT) " +
                "VALUES (?, ?, ?, ?, ?, ?)";
        Connection connection = null;
        PreparedStatement statement = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setLong(1, entry.getTaskId().longValue());
            statement.setString(2, entry.getAction());
            statement.setString(3, entry.getOldValue());
            statement.setString(4, entry.getNewValue());
            statement.setLong(5, entry.getPerformedByUserId().longValue());
            statement.setString(6, DateUtils.formatDateTime(entry.getPerformedAt()));
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Unable to insert audit entry", e);
        } finally {
            close(null, statement, connection);
        }
    }

    public List findAuditEntriesForTask(Long taskId) {
        String sql = "SELECT a.AUDIT_ID, a.TASK_ID, a.ACTION, a.OLD_VALUE, a.NEW_VALUE, " +
                "a.PERFORMED_BY_USER_ID, u.DISPLAY_NAME, a.PERFORMED_AT " +
                "FROM TASK_AUDIT a JOIN APP_USER u ON u.USER_ID = a.PERFORMED_BY_USER_ID " +
                "WHERE a.TASK_ID = ? ORDER BY a.PERFORMED_AT";
        List entries = new ArrayList();
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setLong(1, taskId.longValue());
            resultSet = statement.executeQuery();
            while (resultSet.next()) {
                entries.add(mapEntry(resultSet));
            }
            return entries;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find audit entries", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    public List findActivityReport(Date from, Date to) {
        StringBuffer sql = new StringBuffer();
        List parameters = new ArrayList();
        sql.append("SELECT a.ACTION, u.DISPLAY_NAME, COUNT(*) AS ACTION_COUNT ");
        sql.append("FROM TASK_AUDIT a JOIN APP_USER u ON u.USER_ID = a.PERFORMED_BY_USER_ID WHERE 1 = 1 ");
        if (from != null) {
            sql.append("AND a.PERFORMED_AT >= ? ");
            parameters.add(DateUtils.formatDate(from));
        }
        if (to != null) {
            sql.append("AND a.PERFORMED_AT <= ? ");
            parameters.add(DateUtils.formatDate(to) + "T23:59:59");
        }
        sql.append("GROUP BY a.ACTION, u.DISPLAY_NAME ORDER BY a.ACTION, u.DISPLAY_NAME");

        List rows = new ArrayList();
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql.toString());
            for (int i = 0; i < parameters.size(); i++) {
                statement.setString(i + 1, String.valueOf(parameters.get(i)));
            }
            resultSet = statement.executeQuery();
            while (resultSet.next()) {
                Map row = new LinkedHashMap();
                row.put("action", resultSet.getString("ACTION"));
                row.put("user", resultSet.getString("DISPLAY_NAME"));
                row.put("count", Integer.valueOf(resultSet.getInt("ACTION_COUNT")));
                rows.add(row);
            }
            return rows;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find activity report", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    private TaskAuditEntry mapEntry(ResultSet resultSet) throws SQLException {
        TaskAuditEntry entry = new TaskAuditEntry();
        entry.setAuditId(Long.valueOf(resultSet.getLong("AUDIT_ID")));
        entry.setTaskId(Long.valueOf(resultSet.getLong("TASK_ID")));
        entry.setAction(resultSet.getString("ACTION"));
        entry.setOldValue(resultSet.getString("OLD_VALUE"));
        entry.setNewValue(resultSet.getString("NEW_VALUE"));
        entry.setPerformedByUserId(Long.valueOf(resultSet.getLong("PERFORMED_BY_USER_ID")));
        entry.setPerformedByDisplayName(resultSet.getString("DISPLAY_NAME"));
        entry.setPerformedAt(DateUtils.parseDateTime(resultSet.getString("PERFORMED_AT")));
        return entry;
    }

    private void close(ResultSet resultSet, PreparedStatement statement, Connection connection) {
        try {
            if (resultSet != null) {
                resultSet.close();
            }
            if (statement != null) {
                statement.close();
            }
            if (connection != null) {
                connection.close();
            }
        } catch (SQLException ignored) {
        }
    }
}
