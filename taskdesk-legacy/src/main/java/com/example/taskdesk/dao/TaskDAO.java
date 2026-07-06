package com.example.taskdesk.dao;

import com.example.taskdesk.model.Task;
import com.example.taskdesk.model.TaskComment;
import com.example.taskdesk.model.TaskSearchCriteria;
import com.example.taskdesk.util.DateUtils;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.util.ArrayList;
import java.util.List;

public class TaskDAO {
    private final JdbcConnectionManager connectionManager = JdbcConnectionManager.getInstance();

    public List findTasks(TaskSearchCriteria criteria) {
        StringBuffer sql = new StringBuffer();
        List parameters = new ArrayList();
        sql.append("SELECT t.TASK_ID, t.TITLE, t.DESCRIPTION, t.STATUS, t.PRIORITY, ");
        sql.append("t.OWNER_USER_ID, owner.DISPLAY_NAME AS OWNER_NAME, ");
        sql.append("t.CREATED_BY_USER_ID, creator.DISPLAY_NAME AS CREATOR_NAME, ");
        sql.append("t.CREATED_AT, t.UPDATED_AT, t.DUE_DATE ");
        sql.append("FROM TASK t ");
        sql.append("LEFT JOIN APP_USER owner ON owner.USER_ID = t.OWNER_USER_ID ");
        sql.append("JOIN APP_USER creator ON creator.USER_ID = t.CREATED_BY_USER_ID ");
        sql.append("WHERE 1 = 1 ");
        if (criteria != null && hasText(criteria.getStatus())) {
            sql.append("AND t.STATUS = ? ");
            parameters.add(criteria.getStatus());
        }
        if (criteria != null && hasText(criteria.getPriority())) {
            sql.append("AND t.PRIORITY = ? ");
            parameters.add(criteria.getPriority());
        }
        if (criteria != null && criteria.getOwnerUserId() != null) {
            sql.append("AND t.OWNER_USER_ID = ? ");
            parameters.add(criteria.getOwnerUserId());
        }
        if (criteria != null && criteria.getDueDateFrom() != null) {
            sql.append("AND t.DUE_DATE >= ? ");
            parameters.add(DateUtils.formatDate(criteria.getDueDateFrom()));
        }
        if (criteria != null && criteria.getDueDateTo() != null) {
            sql.append("AND t.DUE_DATE <= ? ");
            parameters.add(DateUtils.formatDate(criteria.getDueDateTo()));
        }
        sql.append("ORDER BY ").append(resolveSortColumn(criteria)).append(" ").append(resolveSortDirection(criteria));
        return queryTasks(sql.toString(), parameters);
    }

    public Task findTaskById(Long taskId) {
        String sql = "SELECT t.TASK_ID, t.TITLE, t.DESCRIPTION, t.STATUS, t.PRIORITY, " +
                "t.OWNER_USER_ID, owner.DISPLAY_NAME AS OWNER_NAME, " +
                "t.CREATED_BY_USER_ID, creator.DISPLAY_NAME AS CREATOR_NAME, " +
                "t.CREATED_AT, t.UPDATED_AT, t.DUE_DATE " +
                "FROM TASK t LEFT JOIN APP_USER owner ON owner.USER_ID = t.OWNER_USER_ID " +
                "JOIN APP_USER creator ON creator.USER_ID = t.CREATED_BY_USER_ID " +
                "WHERE t.TASK_ID = ?";
        List parameters = new ArrayList();
        parameters.add(taskId);
        List tasks = queryTasks(sql, parameters);
        if (tasks.isEmpty()) {
            return null;
        }
        return (Task) tasks.get(0);
    }

    public Long insertTask(Task task) {
        String sql = "INSERT INTO TASK (TITLE, DESCRIPTION, STATUS, PRIORITY, OWNER_USER_ID, " +
                "CREATED_BY_USER_ID, CREATED_AT, UPDATED_AT, DUE_DATE) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)";
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet keys = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql, Statement.RETURN_GENERATED_KEYS);
            bindTaskForInsert(statement, task);
            statement.executeUpdate();
            keys = statement.getGeneratedKeys();
            if (keys.next()) {
                return Long.valueOf(keys.getLong(1));
            }
            throw new RuntimeException("Task insert did not return a generated key");
        } catch (SQLException e) {
            throw new RuntimeException("Unable to insert task", e);
        } finally {
            close(keys, statement, connection);
        }
    }

    public void updateTask(Task task) {
        String sql = "UPDATE TASK SET TITLE = ?, DESCRIPTION = ?, STATUS = ?, PRIORITY = ?, " +
                "OWNER_USER_ID = ?, UPDATED_AT = ?, DUE_DATE = ? WHERE TASK_ID = ?";
        Connection connection = null;
        PreparedStatement statement = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setString(1, task.getTitle());
            statement.setString(2, task.getDescription());
            statement.setString(3, task.getStatus());
            statement.setString(4, task.getPriority());
            setNullableLong(statement, 5, task.getOwnerUserId());
            statement.setString(6, DateUtils.nowDateTime());
            statement.setString(7, DateUtils.formatDate(task.getDueDate()));
            statement.setLong(8, task.getTaskId().longValue());
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Unable to update task", e);
        } finally {
            close(null, statement, connection);
        }
    }

    public void updateTaskStatus(Long taskId, String status) {
        String sql = "UPDATE TASK SET STATUS = ?, UPDATED_AT = ? WHERE TASK_ID = ?";
        Connection connection = null;
        PreparedStatement statement = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setString(1, status);
            statement.setString(2, DateUtils.nowDateTime());
            statement.setLong(3, taskId.longValue());
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Unable to update task status", e);
        } finally {
            close(null, statement, connection);
        }
    }

    public void updateTaskOwner(Long taskId, Long ownerUserId) {
        String sql = "UPDATE TASK SET OWNER_USER_ID = ?, UPDATED_AT = ? WHERE TASK_ID = ?";
        Connection connection = null;
        PreparedStatement statement = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            setNullableLong(statement, 1, ownerUserId);
            statement.setString(2, DateUtils.nowDateTime());
            statement.setLong(3, taskId.longValue());
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Unable to update task owner", e);
        } finally {
            close(null, statement, connection);
        }
    }

    public void insertComment(TaskComment comment) {
        String sql = "INSERT INTO TASK_COMMENT (TASK_ID, AUTHOR_USER_ID, COMMENT_TEXT, CREATED_AT) VALUES (?, ?, ?, ?)";
        Connection connection = null;
        PreparedStatement statement = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setLong(1, comment.getTaskId().longValue());
            statement.setLong(2, comment.getAuthorUserId().longValue());
            statement.setString(3, comment.getCommentText());
            statement.setString(4, DateUtils.formatDateTime(comment.getCreatedAt()));
            statement.executeUpdate();
        } catch (SQLException e) {
            throw new RuntimeException("Unable to insert task comment", e);
        } finally {
            close(null, statement, connection);
        }
    }

    public List findCommentsByTaskId(Long taskId) {
        String sql = "SELECT c.COMMENT_ID, c.TASK_ID, c.AUTHOR_USER_ID, u.DISPLAY_NAME, c.COMMENT_TEXT, c.CREATED_AT " +
                "FROM TASK_COMMENT c JOIN APP_USER u ON u.USER_ID = c.AUTHOR_USER_ID " +
                "WHERE c.TASK_ID = ? ORDER BY c.CREATED_AT";
        List comments = new ArrayList();
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setLong(1, taskId.longValue());
            resultSet = statement.executeQuery();
            while (resultSet.next()) {
                TaskComment comment = new TaskComment();
                comment.setCommentId(Long.valueOf(resultSet.getLong("COMMENT_ID")));
                comment.setTaskId(Long.valueOf(resultSet.getLong("TASK_ID")));
                comment.setAuthorUserId(Long.valueOf(resultSet.getLong("AUTHOR_USER_ID")));
                comment.setAuthorDisplayName(resultSet.getString("DISPLAY_NAME"));
                comment.setCommentText(resultSet.getString("COMMENT_TEXT"));
                comment.setCreatedAt(DateUtils.parseDateTime(resultSet.getString("CREATED_AT")));
                comments.add(comment);
            }
            return comments;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find task comments", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    private List queryTasks(String sql, List parameters) {
        List tasks = new ArrayList();
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            for (int i = 0; i < parameters.size(); i++) {
                Object value = parameters.get(i);
                if (value instanceof Long) {
                    statement.setLong(i + 1, ((Long) value).longValue());
                } else {
                    statement.setString(i + 1, String.valueOf(value));
                }
            }
            resultSet = statement.executeQuery();
            while (resultSet.next()) {
                tasks.add(mapTask(resultSet));
            }
            return tasks;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to query tasks", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    private Task mapTask(ResultSet resultSet) throws SQLException {
        Task task = new Task();
        task.setTaskId(Long.valueOf(resultSet.getLong("TASK_ID")));
        task.setTitle(resultSet.getString("TITLE"));
        task.setDescription(resultSet.getString("DESCRIPTION"));
        task.setStatus(resultSet.getString("STATUS"));
        task.setPriority(resultSet.getString("PRIORITY"));
        long ownerId = resultSet.getLong("OWNER_USER_ID");
        if (!resultSet.wasNull()) {
            task.setOwnerUserId(Long.valueOf(ownerId));
        }
        task.setOwnerDisplayName(resultSet.getString("OWNER_NAME"));
        task.setCreatedByUserId(Long.valueOf(resultSet.getLong("CREATED_BY_USER_ID")));
        task.setCreatedByDisplayName(resultSet.getString("CREATOR_NAME"));
        task.setCreatedAt(DateUtils.parseDateTime(resultSet.getString("CREATED_AT")));
        task.setUpdatedAt(DateUtils.parseDateTime(resultSet.getString("UPDATED_AT")));
        task.setDueDate(DateUtils.parseDate(resultSet.getString("DUE_DATE")));
        return task;
    }

    private void bindTaskForInsert(PreparedStatement statement, Task task) throws SQLException {
        statement.setString(1, task.getTitle());
        statement.setString(2, task.getDescription());
        statement.setString(3, task.getStatus());
        statement.setString(4, task.getPriority());
        setNullableLong(statement, 5, task.getOwnerUserId());
        statement.setLong(6, task.getCreatedByUserId().longValue());
        statement.setString(7, DateUtils.formatDateTime(task.getCreatedAt()));
        statement.setString(8, DateUtils.formatDateTime(task.getUpdatedAt()));
        statement.setString(9, DateUtils.formatDate(task.getDueDate()));
    }

    private String resolveSortColumn(TaskSearchCriteria criteria) {
        if (criteria == null || !hasText(criteria.getSortBy())) {
            return "t.DUE_DATE";
        }
        if ("priority".equals(criteria.getSortBy())) {
            return "t.PRIORITY";
        }
        if ("status".equals(criteria.getSortBy())) {
            return "t.STATUS";
        }
        if ("createdAt".equals(criteria.getSortBy())) {
            return "t.CREATED_AT";
        }
        return "t.DUE_DATE";
    }

    private String resolveSortDirection(TaskSearchCriteria criteria) {
        if (criteria != null && "DESC".equalsIgnoreCase(criteria.getSortDirection())) {
            return "DESC";
        }
        return "ASC";
    }

    private boolean hasText(String value) {
        return value != null && value.trim().length() > 0;
    }

    private void setNullableLong(PreparedStatement statement, int index, Long value) throws SQLException {
        if (value == null) {
            statement.setNull(index, java.sql.Types.INTEGER);
        } else {
            statement.setLong(index, value.longValue());
        }
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
