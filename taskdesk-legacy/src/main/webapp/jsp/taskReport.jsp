<%@ page import="java.util.List" %>
<%@ page import="java.util.Map" %>
<%@ taglib uri="http://struts.apache.org/tags-html" prefix="html" %>
<%@ taglib uri="http://struts.apache.org/tags-bean" prefix="bean" %>
<%@ taglib uri="http://struts.apache.org/tags-logic" prefix="logic" %>
<!DOCTYPE html>
<html>
<head>
    <title><bean:message key="task.report.title"/></title>
    <link rel="stylesheet" href="<%= request.getContextPath() %>/css/taskdesk-legacy.css">
</head>
<body>
<div class="legacy-shell">
<div class="legacy-header">
    <div class="legacy-header-inner">
        <h1 class="legacy-title">TaskDesk Legacy</h1>
        <div class="legacy-subtitle">Manager activity report</div>
    </div>
</div>
<main class="legacy-main">
<p><html:link styleClass="legacy-secondary-link" action="/tasks">Back to list</html:link></p>
<div class="legacy-page">
<div class="legacy-page-header">
    <h1><bean:message key="task.report.title"/></h1>
</div>
<div class="legacy-content">
<html:form action="/taskReport" styleClass="legacy-filter">
    <span class="filter-field">From <html:text property="fromDate" size="10"/></span>
    <span class="filter-field">To <html:text property="toDate" size="10"/></span>
    <span class="filter-field">Group by <html:select property="groupBy">
            <html:option value="action">Action</html:option>
            <html:option value="user">User</html:option>
        </html:select></span>
    <span class="filter-field">Include completed <html:checkbox property="includeCompleted" value="true"/></span>
    <html:submit>Run</html:submit>
</html:form>
<%
    List rows = (List) request.getAttribute("reportRows");
    int total = 0;
    if (rows != null) {
        for (int i = 0; i < rows.size(); i++) {
            Map row = (Map) rows.get(i);
            Object count = row.get("count");
            if (count instanceof Number) {
                total += ((Number) count).intValue();
            }
        }
    }
%>
<p class="legacy-meta">Total audited actions: <%= total %></p>
<table class="legacy-table">
    <tr>
        <th>Action</th>
        <th>User</th>
        <th>Count</th>
    </tr>
    <logic:iterate id="row" name="reportRows">
        <tr>
            <td><bean:write name="row" property="action"/></td>
            <td><bean:write name="row" property="user"/></td>
            <td><bean:write name="row" property="count"/></td>
        </tr>
    </logic:iterate>
</table>
</div>
</div>
</main>
</div>
</body>
</html>
