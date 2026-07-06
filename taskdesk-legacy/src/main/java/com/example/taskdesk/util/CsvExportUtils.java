package com.example.taskdesk.util;

import com.example.taskdesk.model.Task;

import java.util.List;

public final class CsvExportUtils {
    private CsvExportUtils() {
    }

    public static String tasksToCsv(List tasks) {
        StringBuffer buffer = new StringBuffer();
        buffer.append("Task ID,Title,Status,Priority,Owner,Created By,Due Date\n");
        for (int i = 0; i < tasks.size(); i++) {
            Task task = (Task) tasks.get(i);
            buffer.append(task.getTaskId()).append(",");
            buffer.append(escape(task.getTitle())).append(",");
            buffer.append(escape(task.getStatus())).append(",");
            buffer.append(escape(task.getPriority())).append(",");
            buffer.append(escape(task.getOwnerDisplayName())).append(",");
            buffer.append(escape(task.getCreatedByDisplayName())).append(",");
            buffer.append(escape(DateUtils.formatDate(task.getDueDate()))).append("\n");
        }
        return buffer.toString();
    }

    private static String escape(String value) {
        if (value == null) {
            return "";
        }
        String escaped = value.replace("\"", "\"\"");
        if (escaped.indexOf(',') >= 0 || escaped.indexOf('\n') >= 0 || escaped.indexOf('"') >= 0) {
            return "\"" + escaped + "\"";
        }
        return escaped;
    }
}
