package com.example.taskdesk.model;

import java.io.Serializable;
import java.util.Date;

public class TaskSearchCriteria implements Serializable {
    private String status;
    private String priority;
    private Long ownerUserId;
    private Date dueDateFrom;
    private Date dueDateTo;
    private String sortBy;
    private String sortDirection;

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getPriority() {
        return priority;
    }

    public void setPriority(String priority) {
        this.priority = priority;
    }

    public Long getOwnerUserId() {
        return ownerUserId;
    }

    public void setOwnerUserId(Long ownerUserId) {
        this.ownerUserId = ownerUserId;
    }

    public Date getDueDateFrom() {
        return dueDateFrom;
    }

    public void setDueDateFrom(Date dueDateFrom) {
        this.dueDateFrom = dueDateFrom;
    }

    public Date getDueDateTo() {
        return dueDateTo;
    }

    public void setDueDateTo(Date dueDateTo) {
        this.dueDateTo = dueDateTo;
    }

    public String getSortBy() {
        return sortBy;
    }

    public void setSortBy(String sortBy) {
        this.sortBy = sortBy;
    }

    public String getSortDirection() {
        return sortDirection;
    }

    public void setSortDirection(String sortDirection) {
        this.sortDirection = sortDirection;
    }
}
