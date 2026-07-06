package com.example.taskdesk.action;

import com.example.taskdesk.form.TaskReportForm;
import com.example.taskdesk.model.TaskSearchCriteria;
import com.example.taskdesk.service.AuditService;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.util.CsvExportUtils;
import com.example.taskdesk.util.DateUtils;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.PrintWriter;
import java.util.Date;

public class TaskReportAction extends BaseTaskDeskAction {
    private final AuditService auditService = new AuditService();
    private final TaskService taskService = new TaskService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) throws Exception {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        if (isExportRequest(request)) {
            exportCsv(response);
            return null;
        }
        if (!SecurityUtils.isManager(request)) {
            return mapping.findForward("denied");
        }
        TaskReportForm reportForm = (TaskReportForm) form;
        Date from = DateUtils.parseDate(reportForm.getFromDate());
        Date to = DateUtils.parseDate(reportForm.getToDate());
        request.setAttribute("reportRows", auditService.findActivityReport(from, to));
        request.setAttribute("groupBy", hasText(reportForm.getGroupBy()) ? reportForm.getGroupBy() : "action");
        request.setAttribute("includeCompleted", "true".equals(reportForm.getIncludeCompleted()));
        return mapping.findForward("success");
    }

    private boolean isExportRequest(HttpServletRequest request) {
        String path = request.getServletPath();
        return path != null && path.indexOf("taskExport") >= 0;
    }

    private void exportCsv(HttpServletResponse response) throws Exception {
        TaskSearchCriteria criteria = new TaskSearchCriteria();
        response.setContentType("text/csv");
        response.setHeader("Content-Disposition", "attachment; filename=\"taskdesk-tasks.csv\"");
        PrintWriter writer = response.getWriter();
        writer.write(CsvExportUtils.tasksToCsv(taskService.searchTasks(criteria)));
        writer.flush();
    }
}
