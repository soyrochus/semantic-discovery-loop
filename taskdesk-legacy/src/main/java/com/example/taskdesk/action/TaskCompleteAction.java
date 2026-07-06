package com.example.taskdesk.action;

import com.example.taskdesk.model.Task;
import com.example.taskdesk.model.User;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskCompleteAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();

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
        User actor = currentUser(request);
        if (task == null) {
            return mapping.findForward("notFound");
        }
        if (!SecurityUtils.isManager(request) && !actor.getUserId().equals(task.getOwnerUserId())) {
            return mapping.findForward("denied");
        }
        taskService.completeTask(taskId, actor);
        request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "task.complete.success");
        request.setAttribute("task", taskService.findTaskById(taskId));
        request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
        return mapping.findForward("success");
    }
}
