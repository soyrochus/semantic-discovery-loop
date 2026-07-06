<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<!DOCTYPE html>
<html>
<head>
    <title>Access denied</title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Access control</div>
    </div>
</div>
<main class="legacy-main">
<div class="legacy-page">
    <div class="legacy-page-header">
        <h1><bean:message key="error.accessDenied"/></h1>
    </div>
    <div class="legacy-content">
        <p class="legacy-error"><bean:message key="error.accessDenied"/></p>
        <p><html:link action="/tasks">Back to tasks</html:link></p>
    </div>
</div>
</main>
</div>
</body>
</html>
