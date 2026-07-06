package com.example.taskdesk.dao;

import java.io.InputStream;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;
import java.util.Properties;

public class JdbcConnectionManager {
    private static final String DEFAULT_DB_URL = "jdbc:sqlite:../runtime-data/taskdesk-demo.sqlite";
    private static final JdbcConnectionManager INSTANCE = new JdbcConnectionManager();
    private final String databaseUrl;

    private JdbcConnectionManager() {
        this.databaseUrl = loadDatabaseUrl();
        try {
            Class.forName("org.sqlite.JDBC");
        } catch (ClassNotFoundException e) {
            throw new IllegalStateException("SQLite JDBC driver not found", e);
        }
    }

    public static JdbcConnectionManager getInstance() {
        return INSTANCE;
    }

    public Connection getConnection() throws SQLException {
        Connection connection = DriverManager.getConnection(databaseUrl);
        connection.createStatement().execute("PRAGMA foreign_keys = ON");
        return connection;
    }

    private String loadDatabaseUrl() {
        String systemValue = System.getProperty("taskdesk.db.url");
        if (systemValue != null && systemValue.trim().length() > 0) {
            return systemValue.trim();
        }
        String environmentValue = System.getenv("TASKDESK_DB_URL");
        if (environmentValue != null && environmentValue.trim().length() > 0) {
            return environmentValue.trim();
        }
        Properties properties = new Properties();
        InputStream stream = null;
        try {
            stream = Thread.currentThread().getContextClassLoader().getResourceAsStream("taskdesk.properties");
            if (stream != null) {
                properties.load(stream);
                String configured = properties.getProperty("taskdesk.db.url");
                if (configured != null && configured.trim().length() > 0) {
                    return configured.trim();
                }
            }
        } catch (Exception e) {
            return DEFAULT_DB_URL;
        } finally {
            if (stream != null) {
                try {
                    stream.close();
                } catch (Exception ignored) {
                }
            }
        }
        return DEFAULT_DB_URL;
    }
}
