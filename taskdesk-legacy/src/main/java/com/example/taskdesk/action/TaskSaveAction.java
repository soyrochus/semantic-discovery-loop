package com.example.taskdesk.action;

import com.example.taskdesk.form.TaskForm;
import com.example.taskdesk.model.Task;
import com.example.taskdesk.model.User;
import com.example.taskdesk.service.AuditService;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.DateUtils;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionErrors;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;
import org.apache.struts.action.ActionMessage;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskSaveAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();
    private final UserService userService = new UserService();
    private final AuditService auditService = new AuditService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        TaskForm taskForm = (TaskForm) form;
        if ("comment".equals(taskForm.getMode())) {
            return addComment(mapping, request, taskForm);
        }
        ActionErrors errors = validateManually(taskForm);
        if (!errors.isEmpty()) {
            saveErrors(request, errors);
            request.setAttribute("activeUsers", userService.findActiveUsers());
            return mapping.findForward("input");
        }
        User actor = currentUser(request);
        try {
            Task task = toTask(taskForm);
            Long taskId;
            if (task.getTaskId() == null) {
                taskId = taskService.createTask(task, actor);
                request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "Task created.");
            } else {
                taskService.updateTask(task, actor);
                taskId = task.getTaskId();
                request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "Task saved.");
            }
            request.setAttribute("task", taskService.findTaskById(taskId));
            request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
            request.setAttribute("auditEntries", auditService.findAuditEntriesForTask(taskId));
            return mapping.findForward("success");
        } catch (IllegalArgumentException e) {
            errors.add("task", new ActionMessage(e.getMessage()));
            saveErrors(request, errors);
            request.setAttribute("activeUsers", userService.findActiveUsers());
            return mapping.findForward("input");
        }
    }

    private ActionForward addComment(ActionMapping mapping, HttpServletRequest request, TaskForm taskForm) {
        ActionErrors errors = new ActionErrors();
        Long taskId = parseLong(taskForm.getTaskId());
        try {
            taskService.addComment(taskId, taskForm.getCommentText(), currentUser(request));
            request.getSession().setAttribute(SecurityUtils.SESSION_FLASH, "Comment added.");
            request.setAttribute("task", taskService.findTaskById(taskId));
            request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
            request.setAttribute("auditEntries", auditService.findAuditEntriesForTask(taskId));
            return mapping.findForward("success");
        } catch (IllegalArgumentException e) {
            errors.add("commentText", new ActionMessage(e.getMessage()));
            saveErrors(request, errors);
            request.setAttribute("task", taskService.findTaskById(taskId));
            request.setAttribute("comments", taskService.findCommentsByTaskId(taskId));
            request.setAttribute("auditEntries", auditService.findAuditEntriesForTask(taskId));
            return mapping.findForward("success");
        }
    }

    private ActionErrors validateManually(TaskForm form) {
        ActionErrors errors = new ActionErrors();
        if (!hasText(form.getTitle())) {
            errors.add("title", new ActionMessage("task.title.required"));
        }
        if (!hasText(form.getPriority())) {
            errors.add("priority", new ActionMessage("task.priority.required"));
        }
        try {
            DateUtils.parseDate(form.getDueDate());
        } catch (IllegalArgumentException e) {
            errors.add("dueDate", new ActionMessage("task.dueDate.invalid"));
        }
        if ("CRITICAL".equals(form.getPriority()) && !hasText(form.getOwnerUserId())) {
            errors.add("ownerUserId", new ActionMessage("task.owner.requiredForCritical"));
        }
        return errors;
    }

    private Task toTask(TaskForm form) {
        Task task = new Task();
        task.setTaskId(parseLong(form.getTaskId()));
        task.setTitle(form.getTitle());
        task.setDescription(form.getDescription());
        task.setStatus(hasText(form.getStatus()) ? form.getStatus() : "OPEN");
        task.setPriority(form.getPriority());
        task.setOwnerUserId(parseLong(form.getOwnerUserId()));
        task.setDueDate(DateUtils.parseDate(form.getDueDate()));
        return task;
    }
}
