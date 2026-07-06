<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="task.edit.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Task maintenance</div>
    </div>
</div>
<main class="legacy-main">
<p><html:link styleClass="legacy-secondary-link" action="/tasks">Back to list</html:link></p>
<div class="legacy-page">
    <div class="legacy-page-header">
        <h1><bean:message key="task.edit.title"/></h1>
    </div>
    <div class="legacy-content">
        <html:errors/>
        <html:form action="/taskSave" styleClass="legacy-form">
            <html:hidden property="taskId"/>
            <html:hidden property="mode"/>
            <label><bean:message key="task.title"/></label>
            <html:text property="title" size="60"/>
            <label><bean:message key="task.description"/></label>
            <html:textarea property="description"/>
            <label><bean:message key="task.status"/></label>
            <html:select property="status">
                <html:option value="OPEN">OPEN</html:option>
                <html:option value="IN_PROGRESS">IN_PROGRESS</html:option>
                <html:option value="BLOCKED">BLOCKED</html:option>
                <html:option value="COMPLETED">COMPLETED</html:option>
                <html:option value="CANCELLED">CANCELLED</html:option>
            </html:select>
            <label><bean:message key="task.priority"/></label>
            <html:select property="priority">
                <html:option value="LOW">LOW</html:option>
                <html:option value="NORMAL">NORMAL</html:option>
                <html:option value="HIGH">HIGH</html:option>
                <html:option value="CRITICAL">CRITICAL</html:option>
            </html:select>
            <label><bean:message key="task.owner"/></label>
            <html:select property="ownerUserId">
                <html:option value="">Unassigned</html:option>
                <html:optionsCollection name="activeUsers" value="userId" label="displayName"/>
            </html:select>
            <label><bean:message key="task.dueDate"/></label>
            <html:text property="dueDate" size="12"/>
            <p><html:submit>Save</html:submit></p>
        </html:form>
    </div>
</div>
</main>
</div>
</body>
</html>
