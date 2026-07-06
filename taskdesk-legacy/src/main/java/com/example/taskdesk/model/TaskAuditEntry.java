package com.example.taskdesk.model;

import java.io.Serializable;
import java.util.Date;

public class TaskAuditEntry implements Serializable {
    private Long auditId;
    private Long taskId;
    private String action;
    private String oldValue;
    private String newValue;
    private Long performedByUserId;
    private String performedByDisplayName;
    private Date performedAt;

    public Long getAuditId() {
        return auditId;
    }

    public void setAuditId(Long auditId) {
        this.auditId = auditId;
    }

    public Long getTaskId() {
        return taskId;
    }

    public void setTaskId(Long taskId) {
        this.taskId = taskId;
    }

    public String getAction() {
        return action;
    }

    public void setAction(String action) {
        this.action = action;
    }

    public String getOldValue() {
        return oldValue;
    }

    public void setOldValue(String oldValue) {
        this.oldValue = oldValue;
    }

    public String getNewValue() {
        return newValue;
    }

    public void setNewValue(String newValue) {
        this.newValue = newValue;
    }

    public Long getPerformedByUserId() {
        return performedByUserId;
    }

    public void setPerformedByUserId(Long performedByUserId) {
        this.performedByUserId = performedByUserId;
    }

    public String getPerformedByDisplayName() {
        return performedByDisplayName;
    }

    public void setPerformedByDisplayName(String performedByDisplayName) {
        this.performedByDisplayName = performedByDisplayName;
    }

    public Date getPerformedAt() {
        return performedAt;
    }

    public void setPerformedAt(Date performedAt) {
        this.performedAt = performedAt;
    }
}
