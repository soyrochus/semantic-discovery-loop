<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="login.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
    <div class="legacy-login legacy-page">
        <div class="legacy-page-header">
            <h1><bean:message key="login.title"/></h1>
        </div>
        <div class="legacy-content">
            <html:errors/>
            <% if (request.getAttribute("loginError") != null) { %>
                <p class="legacy-error"><bean:message key="login.error.invalidCredentials"/></p>
            <% } %>
            <html:form action="/login" styleClass="legacy-form">
                <label><bean:message key="login.username"/></label>
                <html:text property="username"/>
                <label><bean:message key="login.password"/></label>
                <html:password property="password"/>
                <p><html:submit><bean:message key="login.submit"/></html:submit></p>
            </html:form>
            <p class="legacy-footnote">Demo users: operator1 / demo, operator2 / demo, manager1 / demo</p>
        </div>
    </div>
</div>
</body>
</html>
