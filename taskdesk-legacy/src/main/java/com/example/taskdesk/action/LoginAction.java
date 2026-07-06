package com.example.taskdesk.action;

import com.example.taskdesk.form.LoginForm;
import com.example.taskdesk.model.User;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

public class LoginAction extends BaseTaskDeskAction {
    private final UserService userService = new UserService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        LoginForm loginForm = (LoginForm) form;
        if (!hasText(loginForm.getUsername()) || !hasText(loginForm.getPassword())) {
            request.setAttribute("loginError", "login.error.invalidCredentials");
            return mapping.findForward("input");
        }
        User user = userService.authenticate(loginForm.getUsername(), loginForm.getPassword());
        if (user == null) {
            request.setAttribute("loginError", "login.error.invalidCredentials");
            return mapping.findForward("input");
        }
        HttpSession session = request.getSession(true);
        session.setAttribute(SecurityUtils.SESSION_CURRENT_USER, user);
        session.setAttribute(SecurityUtils.SESSION_CURRENT_ROLE, user.getRole());
        session.setAttribute(SecurityUtils.SESSION_FLASH, "Welcome, " + user.getDisplayName());
        return mapping.findForward("success");
    }
}
