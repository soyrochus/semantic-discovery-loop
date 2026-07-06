package com.example.taskdesk.service;

import com.example.taskdesk.dao.UserDAO;
import com.example.taskdesk.model.User;

import java.util.List;

public class UserService {
    private final UserDAO userDAO = new UserDAO();

    public User authenticate(String username, String password) {
        if (username == null || password == null) {
            return null;
        }
        User user = userDAO.findUserByUsername(username.trim());
        if (user == null || !user.isActive()) {
            return null;
        }
        if (password.equals(user.getPasswordHash())) {
            return user;
        }
        return null;
    }

    public List findActiveUsers() {
        return userDAO.findActiveUsers();
    }

    public User findUserById(Long userId) {
        return userDAO.findUserById(userId);
    }
}
