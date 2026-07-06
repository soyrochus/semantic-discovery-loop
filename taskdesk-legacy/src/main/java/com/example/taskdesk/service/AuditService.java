package com.example.taskdesk.service;

import com.example.taskdesk.dao.AuditDAO;
import com.example.taskdesk.model.TaskAuditEntry;

import java.util.Date;
import java.util.List;

public class AuditService {
    private final AuditDAO auditDAO = new AuditDAO();

    public void record(Long taskId, String action, String oldValue, String newValue, Long performedByUserId) {
        TaskAuditEntry entry = new TaskAuditEntry();
        entry.setTaskId(taskId);
        entry.setAction(action);
        entry.setOldValue(oldValue);
        entry.setNewValue(newValue);
        entry.setPerformedByUserId(performedByUserId);
        entry.setPerformedAt(new Date());
        auditDAO.insertAuditEntry(entry);
    }

    public List findAuditEntriesForTask(Long taskId) {
        return auditDAO.findAuditEntriesForTask(taskId);
    }

    public List findActivityReport(Date from, Date to) {
        return auditDAO.findActivityReport(from, to);
    }
}
