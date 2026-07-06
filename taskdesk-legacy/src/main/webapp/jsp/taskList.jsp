<%@ page import="java.util.List" %>
<%@ page import="com.example.taskdesk.model.Task" %>
<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<%@ taglib uri="http://struts.apache.org/tags-logic" prefix="logic" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="task.list.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Struts 1.x operational task console</div>
    </div>
    <div class="legacy-nav">
        <div class="legacy-nav-inner">
            <html:link action="/tasks">Tasks</html:link>
            <html:link action="/taskEdit">Create task</html:link>
            <logic:equal name="currentRole" scope="session" value="MANAGER">
                <html:link action="/taskReport">Report</html:link>
            </logic:equal>
            <html:link action="/taskExport">Export CSV</html:link>
            <html:link action="/logout">Logout</html:link>
        </div>
    </div>
</div>
<main class="legacy-main">
<div class="legacy-page">
<div class="legacy-page-header">
    <h1><bean:message key="task.list.title"/></h1>
</div>
<div class="legacy-content">
    <logic:present name="flashMessage" scope="session">
        <p class="legacy-flash"><bean:write name="flashMessage" scope="session"/></p>
        <% session.removeAttribute("flashMessage"); %>
    </logic:present>

    <html:form action="/tasks" styleClass="legacy-filter">
        <span class="filter-field">Status <html:select property="status">
            <html:option value="">Any</html:option>
            <html:option value="OPEN">OPEN</html:option>
            <html:option value="IN_PROGRESS">IN_PROGRESS</html:option>
            <html:option value="BLOCKED">BLOCKED</html:option>
            <html:option value="COMPLETED">COMPLETED</html:option>
            <html:option value="CANCELLED">CANCELLED</html:option>
        </html:select></span>
        <span class="filter-field">Priority <html:select property="priority">
            <html:option value="">Any</html:option>
            <html:option value="LOW">LOW</html:option>
            <html:option value="NORMAL">NORMAL</html:option>
            <html:option value="HIGH">HIGH</html:option>
            <html:option value="CRITICAL">CRITICAL</html:option>
        </html:select></span>
        <span class="filter-field">Owner <html:select property="ownerUserId">
            <html:option value="">Any</html:option>
            <html:optionsCollection name="activeUsers" value="userId" label="displayName"/>
        </html:select></span>
        <span class="filter-field">Due from <html:text property="dueDateFrom" size="10"/></span>
        <span class="filter-field">Due to <html:text property="dueDateTo" size="10"/></span>
        <html:hidden property="sortBy" value="dueDate"/>
        <html:hidden property="sortDirection" value="ASC"/>
        <html:submit>Filter</html:submit>
    </html:form>

<%
    List taskRows = (List) request.getAttribute("tasks");
    int openCount = 0;
    if (taskRows != null) {
        for (int i = 0; i < taskRows.size(); i++) {
            Task task = (Task) taskRows.get(i);
            if (!"COMPLETED".equals(task.getStatus())) {
                openCount++;
            }
        }
    }
%>
    <p class="legacy-meta"><%= openCount %> open or active task(s) in this view.</p>

<table class="legacy-table">
    <tr>
        <th>ID</th>
        <th>Title</th>
        <th>Status</th>
        <th>Priority</th>
        <th>Owner</th>
        <th>Due Date</th>
        <th>Actions</th>
    </tr>
    <logic:iterate id="task" name="tasks">
        <tr>
            <td><bean:write name="task" property="taskId"/></td>
            <td><bean:write name="task" property="title"/></td>
            <td><span class="legacy-status"><bean:write name="task" property="status"/></span></td>
            <td>
                <logic:equal name="task" property="priority" value="CRITICAL"><span class="legacy-critical"></logic:equal>
                <bean:write name="task" property="priority"/>
                <logic:equal name="task" property="priority" value="CRITICAL"></span></logic:equal>
            </td>
            <td><bean:write name="task" property="ownerDisplayName"/></td>
            <td><bean:write name="task" property="dueDate"/></td>
            <td class="legacy-actions">
                <html:link action="/taskDetail" paramId="taskId" paramName="task" paramProperty="taskId">Detail</html:link>
                <logic:notEqual name="task" property="status" value="COMPLETED">
                    <html:link action="/taskEdit" paramId="taskId" paramName="task" paramProperty="taskId">Edit</html:link>
                </logic:notEqual>
            </td>
        </tr>
    </logic:iterate>
</table>
</div>
</div>
</main>
</div>
</body>
</html>
