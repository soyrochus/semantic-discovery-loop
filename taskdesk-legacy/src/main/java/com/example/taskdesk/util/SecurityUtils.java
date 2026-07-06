package com.example.taskdesk.util;

import com.example.taskdesk.model.User;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpSession;

public final class SecurityUtils {
    public static final String SESSION_CURRENT_USER = "currentUser";
    public static final String SESSION_CURRENT_ROLE = "currentRole";
    public static final String SESSION_LAST_SEARCH = "lastTaskSearchFilter";
    public static final String SESSION_LAST_TASK_ID = "lastVisitedTaskId";
    public static final String SESSION_FLASH = "flashMessage";

    private SecurityUtils() {
    }

    public static User currentUser(HttpServletRequest request) {
        HttpSession session = request.getSession(false);
        if (session == null) {
            return null;
        }
        Object value = session.getAttribute(SESSION_CURRENT_USER);
        if (value instanceof User) {
            return (User) value;
        }
        return null;
    }

    public static boolean isLoggedIn(HttpServletRequest request) {
        return currentUser(request) != null;
    }

    public static boolean isManager(HttpServletRequest request) {
        User user = currentUser(request);
        return user != null && "MANAGER".equals(user.getRole());
    }

    public static boolean isOperator(HttpServletRequest request) {
        User user = currentUser(request);
        return user != null && "OPERATOR".equals(user.getRole());
    }

    public static void requireLogin(HttpServletRequest request) {
        if (!isLoggedIn(request)) {
            throw new SecurityException("Login required");
        }
    }
}
