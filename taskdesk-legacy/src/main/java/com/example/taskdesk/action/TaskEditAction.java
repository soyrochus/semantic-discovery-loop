package com.example.taskdesk.action;

import com.example.taskdesk.form.TaskForm;
import com.example.taskdesk.model.Task;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.DateUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskEditAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();
    private final UserService userService = new UserService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        TaskForm taskForm = (TaskForm) form;
        Long taskId = parseLong(request.getParameter("taskId"));
        if (taskId == null) {
            taskForm.setMode("create");
            taskForm.setStatus("OPEN");
            taskForm.setPriority("NORMAL");
        } else {
            Task task = taskService.findTaskById(taskId);
            if (task == null) {
                return mapping.findForward("notFound");
            }
            if ("COMPLETED".equals(task.getStatus())) {
                request.setAttribute("errorMessage", "task.status.completedCannotEdit");
                return mapping.findForward("error");
            }
            populateForm(taskForm, task);
        }
        request.setAttribute("activeUsers", userService.findActiveUsers());
        return mapping.findForward("success");
    }

    private void populateForm(TaskForm form, Task task) {
        form.setMode("edit");
        form.setTaskId(String.valueOf(task.getTaskId()));
        form.setTitle(task.getTitle());
        form.setDescription(task.getDescription());
        form.setStatus(task.getStatus());
        form.setPriority(task.getPriority());
        form.setOwnerUserId(task.getOwnerUserId() == null ? "" : String.valueOf(task.getOwnerUserId()));
        form.setDueDate(DateUtils.formatDate(task.getDueDate()));
    }
}
