package com.example.taskdesk.dao;

import com.example.taskdesk.model.User;

import java.sql.Connection;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.util.ArrayList;
import java.util.List;

public class UserDAO {
    private final JdbcConnectionManager connectionManager = JdbcConnectionManager.getInstance();

    public User findUserByUsername(String username) {
        String sql = "SELECT USER_ID, USERNAME, PASSWORD_HASH, DISPLAY_NAME, ROLE, ACTIVE " +
                "FROM APP_USER WHERE USERNAME = ?";
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setString(1, username);
            resultSet = statement.executeQuery();
            if (resultSet.next()) {
                return mapUser(resultSet);
            }
            return null;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find user by username", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    public List findActiveUsers() {
        String sql = "SELECT USER_ID, USERNAME, PASSWORD_HASH, DISPLAY_NAME, ROLE, ACTIVE " +
                "FROM APP_USER WHERE ACTIVE = 1 ORDER BY DISPLAY_NAME";
        List users = new ArrayList();
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            resultSet = statement.executeQuery();
            while (resultSet.next()) {
                users.add(mapUser(resultSet));
            }
            return users;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find active users", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    public User findUserById(Long userId) {
        String sql = "SELECT USER_ID, USERNAME, PASSWORD_HASH, DISPLAY_NAME, ROLE, ACTIVE " +
                "FROM APP_USER WHERE USER_ID = ?";
        Connection connection = null;
        PreparedStatement statement = null;
        ResultSet resultSet = null;
        try {
            connection = connectionManager.getConnection();
            statement = connection.prepareStatement(sql);
            statement.setLong(1, userId.longValue());
            resultSet = statement.executeQuery();
            if (resultSet.next()) {
                return mapUser(resultSet);
            }
            return null;
        } catch (SQLException e) {
            throw new RuntimeException("Unable to find user by id", e);
        } finally {
            close(resultSet, statement, connection);
        }
    }

    private User mapUser(ResultSet resultSet) throws SQLException {
        User user = new User();
        user.setUserId(Long.valueOf(resultSet.getLong("USER_ID")));
        user.setUsername(resultSet.getString("USERNAME"));
        user.setPasswordHash(resultSet.getString("PASSWORD_HASH"));
        user.setDisplayName(resultSet.getString("DISPLAY_NAME"));
        user.setRole(resultSet.getString("ROLE"));
        user.setActive(resultSet.getInt("ACTIVE") == 1);
        return user;
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
