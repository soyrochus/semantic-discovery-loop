<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<%@ page import="com.example.taskdesk.model.Task" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="task.assign.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Manager assignment workflow</div>
    </div>
</div>
<main class="legacy-main">
<p><html:link styleClass="legacy-secondary-link" action="/tasks">Back to list</html:link></p>
<div class="legacy-page">
<div class="legacy-page-header">
    <h1><bean:message key="task.assign.title"/></h1>
</div>
<div class="legacy-content">
    <html:errors/>
<%
    String assignTaskId = request.getParameter("taskId");
    if (assignTaskId == null && request.getAttribute("task") != null) {
        Task assignTask = (Task) request.getAttribute("task");
        assignTaskId = String.valueOf(assignTask.getTaskId());
    }
    if (assignTaskId == null) {
        assignTaskId = "";
    }
%>
<html:form action="/taskAssign" styleClass="legacy-form">
    <input type="hidden" name="taskId" value="<%= assignTaskId %>"/>
    <label><bean:message key="task.owner"/></label>
    <html:select property="ownerUserId">
        <html:optionsCollection name="activeUsers" value="userId" label="displayName"/>
    </html:select>
    <label>Assignment reason</label>
    <html:textarea property="assignmentReason"/>
    <p><html:submit>Assign</html:submit></p>
</html:form>
</div>
</div>
</main>
</div>
</body>
</html>
