package com.example.taskdesk.action;

import com.example.taskdesk.form.TaskSearchForm;
import com.example.taskdesk.model.TaskSearchCriteria;
import com.example.taskdesk.model.User;
import com.example.taskdesk.service.TaskService;
import com.example.taskdesk.service.UserService;
import com.example.taskdesk.util.DateUtils;
import com.example.taskdesk.util.SecurityUtils;
import org.apache.struts.action.ActionForm;
import org.apache.struts.action.ActionForward;
import org.apache.struts.action.ActionMapping;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;

public class TaskListAction extends BaseTaskDeskAction {
    private final TaskService taskService = new TaskService();
    private final UserService userService = new UserService();

    public ActionForward execute(ActionMapping mapping, ActionForm form, HttpServletRequest request,
                                 HttpServletResponse response) {
        ActionForward login = requireLogin(mapping, request);
        if (login != null) {
            return login;
        }
        TaskSearchForm searchForm = (TaskSearchForm) form;
        TaskSearchCriteria criteria = toCriteria(searchForm);
        User user = currentUser(request);
        if ("OPERATOR".equals(user.getRole()) && criteria.getOwnerUserId() == null) {
            criteria.setOwnerUserId(user.getUserId());
            searchForm.setOwnerUserId(String.valueOf(user.getUserId()));
        }
        request.getSession().setAttribute(SecurityUtils.SESSION_LAST_SEARCH, criteria);
        request.setAttribute("tasks", taskService.searchTasks(criteria));
        request.setAttribute("activeUsers", userService.findActiveUsers());
        return mapping.findForward("success");
    }

    private TaskSearchCriteria toCriteria(TaskSearchForm form) {
        TaskSearchCriteria criteria = new TaskSearchCriteria();
        criteria.setStatus(emptyToNull(form.getStatus()));
        criteria.setPriority(emptyToNull(form.getPriority()));
        criteria.setOwnerUserId(parseLong(form.getOwnerUserId()));
        criteria.setDueDateFrom(DateUtils.parseDate(form.getDueDateFrom()));
        criteria.setDueDateTo(DateUtils.parseDate(form.getDueDateTo()));
        criteria.setSortBy(emptyToNull(form.getSortBy()));
        criteria.setSortDirection(emptyToNull(form.getSortDirection()));
        return criteria;
    }

    private String emptyToNull(String value) {
        return hasText(value) ? value.trim() : null;
    }
}
