<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<!DOCTYPE html>
<html>
<head>
    <title>Error</title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Error</div>
    </div>
</div>
<main class="legacy-main">
<div class="legacy-page">
    <div class="legacy-page-header">
        <h1><bean:message key="error.general"/></h1>
    </div>
    <div class="legacy-content">
        <p class="legacy-error"><bean:write name="errorMessage" ignore="true"/></p>
        <p><html:link action="/tasks">Back to tasks</html:link></p>
    </div>
</div>
</main>
</div>
</body>
</html>
