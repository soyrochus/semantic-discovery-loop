package com.example.taskdesk.action;

import com.example.taskdesk.model.User;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskReopenAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        if (!SecurityUtils.isManager(request)) {
            return mapping.findForward("denied");
        }
        Long taskId = parseLong(request.getParameter("taskId"));
        if (taskId == null) {
            return mapping.findForward("notFound");
        }
        User actor = currentUser(request);
        taskService.reopenTask(taskId, actor);
        request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "task.reopen.success");
        request.setAttribute("task", taskService.findTaskById(taskId));
        request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
        return mapping.findForward("success");
    }
}
