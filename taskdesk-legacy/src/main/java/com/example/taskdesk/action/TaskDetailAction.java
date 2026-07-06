package com.example.taskdesk.action;

import com.example.taskdesk.model.Task;
import com.example.taskdesk.service.AuditService;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskDetailAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();
    private final AuditService auditService = new AuditService();
    private final UserService userService = new UserService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        Long taskId = parseLong(request.getParameter("taskId"));
        if (taskId == null) {
            return mapping.findForward("notFound");
        }
        Task task = taskService.findTaskById(taskId);
        if (task == null) {
            return mapping.findForward("notFound");
        }
        request.getSession().setAttribute(SecurityUtils.SESSION_LAST_TASK_ID, taskId);
        request.setAttribute("task", task);
        request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
        request.setAttribute("auditEntries", auditService.findAuditEntriesForTask(taskId));
        request.setAttribute("activeUsers", userService.findActiveUsers());
        return mapping.findForward("success");
    }
}
