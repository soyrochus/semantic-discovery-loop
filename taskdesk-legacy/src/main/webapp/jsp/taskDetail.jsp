<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<%@ taglib uri="http://struts.apache.org/tags-logic" prefix="logic" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="task.detail.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Task detail and activity history</div>
    </div>
</div>
<main class="legacy-main">
<p><html:link styleClass="legacy-secondary-link" action="/tasks">Back to list</html:link></p>
<div class="legacy-page">
<div class="legacy-page-header">
    <h1><bean:write name="task" property="title"/></h1>
</div>
<div class="legacy-content">
    <logic:present name="flashMessage" scope="session">
        <p class="legacy-flash"><bean:write name="flashMessage" scope="session"/></p>
        <% session.removeAttribute("flashMessage"); %>
    </logic:present>
<dl class="legacy-detail-grid">
    <dt>Status</dt><dd><bean:write name="task" property="status"/></dd>
    <dt>Priority</dt><dd><bean:write name="task" property="priority"/></dd>
    <dt>Owner</dt><dd><bean:write name="task" property="ownerDisplayName"/></dd>
    <dt>Created By</dt><dd><bean:write name="task" property="createdByDisplayName"/></dd>
    <dt>Due Date</dt><dd><bean:write name="task" property="dueDate"/></dd>
    <dt>Description</dt><dd><bean:write name="task" property="description"/></dd>
</dl>

<logic:notEqual name="task" property="status" value="COMPLETED">
    <html:link action="/taskEdit" paramId="taskId" paramName="task" paramProperty="taskId">Edit</html:link>
    <html:link action="/taskComplete" paramId="taskId" paramName="task" paramProperty="taskId">Complete</html:link>
</logic:notEqual>
<logic:equal name="currentRole" scope="session" value="MANAGER">
    <html:link action="/taskAssign" paramId="taskId" paramName="task" paramProperty="taskId">Assign</html:link>
    <logic:equal name="task" property="status" value="COMPLETED">
        <html:link action="/taskReopen" paramId="taskId" paramName="task" paramProperty="taskId">Reopen</html:link>
    </logic:equal>
</logic:equal>

<div class="legacy-section">
    <h2>Add Comment</h2>
    <html:form action="/taskSave" styleClass="legacy-form">
        <bean:define id="detailTaskId" name="task" property="taskId"/>
        <input type="hidden" name="taskId" value="<%= String.valueOf(detailTaskId) %>"/>
        <input type="hidden" name="mode" value="comment"/>
        <html:textarea property="commentText"/>
        <p><html:submit>Add comment</html:submit></p>
    </html:form>
</div>

<div class="legacy-section">
    <h2>Comments</h2>
    <ul class="legacy-list">
        <logic:iterate id="comment" name="comments">
            <li><bean:write name="comment" property="authorDisplayName"/>:
                <bean:write name="comment" property="commentText"/></li>
        </logic:iterate>
    </ul>
</div>

<logic:present name="auditEntries">
    <div class="legacy-section">
        <h2>Audit</h2>
        <ul class="legacy-list">
            <logic:iterate id="entry" name="auditEntries">
                <li><bean:write name="entry" property="action"/> by <bean:write name="entry" property="performedByDisplayName"/></li>
            </logic:iterate>
        </ul>
    </div>
</logic:present>
</div>
</div>
</main>
</div>
</body>
</html>
