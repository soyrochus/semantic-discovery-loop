package com.example.taskdesk.action;

import com.example.taskdesk.model.User;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.Action;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;

public abstract class BaseTaskDeskAction extends Action {
    protected User currentUser(HttpServletRequest request) {
        return SecurityUtils.currentUser(request);
    }

    protected ActionForward requireLogin(ActionMapping mapping, HttpServletRequest request) {
        if (!SecurityUtils.isLoggedIn(request)) {
            request.getSession(true).setAttribute(SecurityUtils.SESSION_FLASH, "Please sign in to continue.");
            return mapping.findForward("login");
        }
        return null;
    }

    protected Long parseLong(String value) {
        if (value == null || value.trim().length() == 0) {
            return null;
        }
        return Long.valueOf(value.trim());
    }

    protected boolean hasText(String value) {
        return value != null && value.trim().length() > 0;
    }
}
