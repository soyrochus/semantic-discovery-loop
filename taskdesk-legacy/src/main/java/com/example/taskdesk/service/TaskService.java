package com.example.taskdesk.service;

import com.example.taskdesk.dao.TaskDAO;
import com.example.taskdesk.model.Task;
import com.example.taskdesk.model.TaskComment;
import com.example.taskdesk.model.TaskSearchCriteria;
import com.example.taskdesk.model.User;

import java.util.Date;
import java.util.List;

public class TaskService {
    private final TaskDAO taskDAO = new TaskDAO();
    private final AuditService auditService = new AuditService();

    public List searchTasks(TaskSearchCriteria criteria) {
        return taskDAO.findTasks(criteria);
    }

    public Task findTaskById(Long taskId) {
        return taskDAO.findTaskById(taskId);
    }

    public Long createTask(Task task, User actor) {
        if (task.getStatus() == null || task.getStatus().trim().length() == 0) {
            task.setStatus("OPEN");
        }
        validateTaskForSave(task, null);
        task.setCreatedByUserId(actor.getUserId());
        task.setCreatedAt(new Date());
        Long taskId = taskDAO.insertTask(task);
        auditService.record(taskId, "CREATE_TASK", null, task.getStatus(), actor.getUserId());
        return taskId;
    }

    public void updateTask(Task task, User actor) {
        Task existing = taskDAO.findTaskById(task.getTaskId());
        if (existing == null) {
            throw new IllegalArgumentException("Task not found");
        }
        validateTaskForSave(task, existing);
        taskDAO.updateTask(task);
        auditService.record(task.getTaskId(), "UPDATE_TASK", existing.getStatus(), task.getStatus(), actor.getUserId());
    }

    public void completeTask(Long taskId, User actor) {
        Task existing = requireTask(taskId);
        taskDAO.updateTaskStatus(taskId, "COMPLETED");
        auditService.record(taskId, "CHANGE_STATUS", existing.getStatus(), "COMPLETED", actor.getUserId());
    }

    public void reopenTask(Long taskId, User actor) {
        Task existing = requireTask(taskId);
        taskDAO.updateTaskStatus(taskId, "OPEN");
        auditService.record(taskId, "CHANGE_STATUS", existing.getStatus(), "OPEN", actor.getUserId());
    }

    public void assignTask(Long taskId, Long ownerUserId, String reason, User actor) {
        Task existing = requireTask(taskId);
        String oldValue = existing.getOwnerUserId() == null ? null : String.valueOf(existing.getOwnerUserId());
        taskDAO.updateTaskOwner(taskId, ownerUserId);
        auditService.record(taskId, "ASSIGN_TASK", oldValue, String.valueOf(ownerUserId), actor.getUserId());
        if (reason != null && reason.trim().length() > 0) {
            addComment(taskId, "Assignment note: " + reason, actor);
        }
    }

    public void addComment(Long taskId, String commentText, User actor) {
        if (commentText == null || commentText.trim().length() == 0) {
            throw new IllegalArgumentException("Comment text is required");
        }
        requireTask(taskId);
        TaskComment comment = new TaskComment();
        comment.setTaskId(taskId);
        comment.setAuthorUserId(actor.getUserId());
        comment.setCommentText(commentText.trim());
        comment.setCreatedAt(new Date());
        taskDAO.insertComment(comment);
        auditService.record(taskId, "ADD_COMMENT", null, "COMMENT", actor.getUserId());
    }

    public List findCommentsByTaskId(Long taskId) {
        return taskDAO.findCommentsByTaskId(taskId);
    }

    private void validateTaskForSave(Task task, Task existing) {
        if (task.getTitle() == null || task.getTitle().trim().length() == 0) {
            throw new IllegalArgumentException("task.title.required");
        }
        if (task.getPriority() == null || task.getPriority().trim().length() == 0) {
            throw new IllegalArgumentException("task.priority.required");
        }
        if ("CRITICAL".equals(task.getPriority()) && task.getOwnerUserId() == null) {
            throw new IllegalArgumentException("task.owner.requiredForCritical");
        }
        if (existing != null && "COMPLETED".equals(existing.getStatus())) {
            throw new IllegalArgumentException("task.status.completedCannotEdit");
        }
        if (task.getDueDate() != null) {
            Date compareDate = existing == null ? new Date() : existing.getCreatedAt();
            if (compareDate != null && task.getDueDate().before(stripTime(compareDate))) {
                throw new IllegalArgumentException("task.dueDate.beforeCreated");
            }
        }
    }

    private Date stripTime(Date date) {
        return new Date(date.getYear(), date.getMonth(), date.getDate());
    }

    private Task requireTask(Long taskId) {
        Task existing = taskDAO.findTaskById(taskId);
        if (existing == null) {
            throw new IllegalArgumentException("Task not found");
        }
        return existing;
    }
}
