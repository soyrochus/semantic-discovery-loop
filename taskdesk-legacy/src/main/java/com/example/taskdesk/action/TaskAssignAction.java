package com.example.taskdesk.action;

import com.example.taskdesk.form.TaskAssignForm;
import com.example.taskdesk.model.User;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskAssignAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();
    private final UserService userService = new UserService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        if (!SecurityUtils.isManager(request)) {
            return mapping.findForward("denied");
        }
        TaskAssignForm assignForm = (TaskAssignForm) form;
        Long taskId = parseLong(firstNonEmpty(assignForm.getTaskId(), request.getParameter("taskId")));
        if (taskId == null) {
            return mapping.findForward("notFound");
        }
        if (request.getMethod().equalsIgnoreCase("GET")) {
            request.setAttribute("task", taskService.findTaskById(taskId));
            request.setAttribute("activeUsers", userService.findActiveUsers());
            return mapping.findForward("input");
        }
        Long ownerUserId = parseLong(assignForm.getOwnerUserId());
        User actor = currentUser(request);
        taskService.assignTask(taskId, ownerUserId, assignForm.getAssignmentReason(), actor);
        request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "task.assign.success");
        request.setAttribute("task", taskService.findTaskById(taskId));
        request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
        return mapping.findForward("success");
    }

    private String firstNonEmpty(String left, String right) {
        return hasText(left) ? left : right;
    }
}
