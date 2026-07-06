package com.example.taskdesk.form;

import org.apache.struts.action.ActionForm;

public class TaskReportForm extends ActionForm {
    private String fromDate;
    private String toDate;
    private String groupBy;
    private String includeCompleted;

    public String getFromDate() {
        return fromDate;
    }

    public void setFromDate(String fromDate) {
        this.fromDate = fromDate;
    }

    public String getToDate() {
        return toDate;
    }

    public void setToDate(String toDate) {
        this.toDate = toDate;
    }

    public String getGroupBy() {
        return groupBy;
    }

    public void setGroupBy(String groupBy) {
        this.groupBy = groupBy;
    }

    public String getIncludeCompleted() {
        return includeCompleted;
    }

    public void setIncludeCompleted(String includeCompleted) {
        this.includeCompleted = includeCompleted;
    }
}
