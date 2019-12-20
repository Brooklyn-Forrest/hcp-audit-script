# HCP Audit Script
# Version 1.9
# Version Notes:
# -Proxy problem resolved
# -Code cleanup
# -Changes to how data is organized, work for text to html conversion

import os
from datetime import datetime
import requests
import re
from bs4 import BeautifulSoup
import csv
import subprocess
import pandas

try:
    del os.environ["HTTP_PROXY"]
    del os.environ["HTTPS_PROXY"]
except Exception as e:
    pass

class filehandling:

    def __init__(self):
        # Date and time
        timestamp = datetime.now()

        self.currenttime = timestamp.strftime("%x, %X")
        self.currentdate = timestamp.strftime("%m-%d-%Y")

        currentmonth = timestamp.strftime("%B")
        currentyear = self.currentdate[6:]

        # File path info
        self.prefix = "Redacted"
        self.pathtocredentials = "Redacted"

fileinfo = filehandling()

class requestinfo:

    def __init__(self):
        self.cookieVal = ""
        self.j_username = ""
        self.j_password = ""

    def call(self, trueUrl, secondaryUrl, adminf, nonadminf, servicef):
        # Python curl command data
        cookies = {
            '_ga': 'GA(IP ADDRESS)',
            '_gid': 'GA(IP ADDRESS)',
            'ajs_anonymous_id': '%2200000000000000000000000000%22',
            'JSESSIONID': 'ojgq4gdu5t4a19bzo0c16xvo5',
        }

        headers = {
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Origin': trueUrl,
            'Upgrade-Insecure-Requests': '1',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Referer': secondaryUrl,
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        with open(fileinfo.pathtocredentials, "r") as authFile:
            self.j_username = authFile.readline()
            self.j_password = authFile.readline()
            self.j_username = self.j_username.rstrip("\n")

        data = {
            'j_username': self.j_username,
            'j_password': self.j_password
        }

        try:
            response = requests.post(trueUrl + '/j_security_check', headers=headers, cookies=cookies, data=data, verify=False, timeout=250)
            self.cookieVal = response.cookies
        except requests.exceptions.RequestException as e:
            print(e)
            return 1
        securityUResponse = requests.get(trueUrl + '/cluster/users_input.action', cookies=self.cookieVal, verify=False, timeout=250)

        tableFetchResponse = requests.get(
            trueUrl + '/cluster/users_tableData.action?reverse=false&sortBy=&targetName=&filterString=&filterType',
            cookies=self.cookieVal, verify=False, timeout=150)

        # Regex to retrieve internal fetch function uniqueIdEncoded values
        regexGeneral = re.findall('[\w-]{23}&rowIndex=[0-9]+', tableFetchResponse.text)
        tenantPage = requests.get(trueUrl + "/cluster/tenants_tableData.action?reverse=false&count=500",
                                  cookies=self.cookieVal, verify=False)

        storageFile = "storedHTML" + ".html"
        with open(storageFile, "w") as file:
            file.write(tenantPage.text)
            file.close()

        with open(storageFile, "r") as htmlobj:
            html = htmlobj.read()

        def text_from_html(html):
            soup = BeautifulSoup(html, 'html.parser')
            texts = soup.findAll(text=True)
            # visible_texts = filter(tag_visible, texts)
            return u" ".join(t.strip() for t in texts)

        listLine = text_from_html(html)
        finalList = listLine.split("Dropdown Information")  # Finally a version of the lines we wanted
      
        truelist = []
        for line in finalList:
            match = re.findall("[a-zA-Z]+", line)
            try:
                truelist.append(match[0])
            except:
                pass
        return(truelist)

    def processuser(self, cookieVal):

        tableFetchResponse = requests.get(
            trueUrl + '/cluster/users_tableData.action?reverse=false&sortBy=&targetName=&filterString=&filterType',
            cookies=cookieVal, verify=False)

        # Search for user IDs
        regexGeneral = re.findall('[\w-]{23}&rowIndex=[0-9]+', tableFetchResponse.text)

        # Iterate through each ID for information
        adminlist = []
        nonadminlist = []
        servicelist = []
        for i in regexGeneral:
            info = []
            urlString = trueUrl + "/cluster/userEdit_input.action?uniqueIdEncoded=" + i
            # print("Value of i: " + i)
            print("\nRequesting html information from individual account...")

            # Parent HTML
            indivHTMLResponse = requests.post(urlString, cookies=cookieVal, verify=False)
            print(indivHTMLResponse)

            regexSearchName = re.findall('input type=\"text\" name=\"user_name\" value=\".+\" id',
                                         indivHTMLResponse.text)
            nameFilter = regexSearchName[0]
            nameFiltered = nameFilter[42:len(nameFilter) - 4]
            info.append(nameFiltered)
            regexSearchFullName = re.findall('input type=\"text\" name=\"full_name\" value=\".+\" id',
                                             indivHTMLResponse.text)
            fullFilter = regexSearchFullName[0]
            fullFiltered = fullFilter[42:len(fullFilter) - 4]
            info.append(fullFiltered)
            regexValidateAdminAccounts = re.findall('name=\"role_system\" value=\"true\" checked=\"checked\"',
                                                    indivHTMLResponse.text)
            if regexValidateAdminAccounts:
                info.append("Yes")
            else:
                info.append("No")
            if "Yes" in info:
                adminlist.append(info)
            else:
                regexdt = re.search('[dD][tT][0-9]{6}|[dD][tT][0-9]{5}', str(info))
                if regexdt:
                    nonadminlist.append(info)
                else:
                    servicelist.append(info)

        return [adminlist, nonadminlist, servicelist]


def writehtml(filesint, title, tenants, admins, nonadmins, service, sys):
    prefixlocal = "Redacted"
    prefixweb = "Redacted"

    def infoappend(folder, text, currfile):
        currfile.writelines(
            '<form id="info" hidden action="converttohtml.php" method="post">'
            '<label for="url" hidden>Url</label>'
            '<input hidden id="url" name="url" '
            'value="' + prefixweb + title + "/" + folder + text + fileinfo.currentdate + '.html">'
            '<label for="path"></label>'
            '<input hidden id="path" name="path" '
            'value="' + prefixlocal + title + '/PDFS/x_on-demand/">'
            '<label for="pathalt"></label>'
            '<input hidden id="pathalt" name="pathalt" '
            'value="' + prefixweb + title + '/PDFS/x_on-demand/">'
            '</form><button onclick="info.submit()">Convert to PDF</button></html>')

    for enum, file in enumerate(filesint):
            with open(file, 'a') as internalf:
                internalf.write("<!DOCTYPE HTML>\n<link rel='stylesheet' href='index.css'>\n<head>"
                         "\n<title>View HTML- HCP</title>\n</head>\n<body>\n")
                if enum == 0:
                    internalf.write("<table><caption>" + title + "</caption><thead><tr><td>User ID</td><td>User Name</td><td>Admin</td></tr></thead>\n")
                    for datagroup in admins:
                        internalf.write("<tr>\n")  # Open row
                        internalf.write("<td>" + datagroup[0] + "</td>\n")  # User ID
                        internalf.write("<td>" + datagroup[1] + "<td>\n")   # User Name
                        internalf.write("<td>" + datagroup[2] + "</td>\n")  # Admin y/n
                        internalf.write("</tr>\n")  # Close row
                    internalf.write("</table>\n")  # Close table
                    infoappend("Human_Admin", "/" + sys + "HCP_Admin_Audit_", internalf)
                    internalf.close()
                elif enum == 1:
                    internalf.write("<table><caption>" + title + "</caption><thead><tr><td>User ID</td><td>User Name</td><td>Admin</td></tr></thead>\n")
                    for datagroup2 in nonadmins:
                        internalf.write("<tr>\n")  # Open row
                        internalf.write("<td>" + datagroup2[0] + "</td>\n")  # User ID
                        internalf.write("<td>" + datagroup2[1] + "<td>\n")  # User Name
                        internalf.write("<td>" + datagroup2[2] + "</td>\n")  # Admin y/n
                        internalf.write("</tr>\n")  # Close row
                    internalf.write("</table>\n")  # End table

                    infoappend("Human_Non_Admin", "/" + sys + "HCP_Non-Admin_Audit_", internalf)
                    internalf.close()

                elif enum == 2:
                    internalf.write("<table><caption>" + title + "</caption><thead><tr><td>Object Username</td></tr></thead>")
                    for datagroup in tenants:
                        # print(datagroup)
                        internalf.write("<tr>\n")  # Open row
                        internalf.write("<td>" + datagroup + "</td>\n")  # Object Username
                        internalf.write("</tr>\n")  # Close row
                    internalf.write("</table>\n")  # End table
                    infoappend("Tenants", "/" + sys + "HCP_Tenants_", internalf)
                    internalf.close()
                elif enum == 3:
                    internalf.write("<table><caption>" + title + "</caption><thead><tr><td>Service Account ID</td><td>Description</td><td>Admin Status</td></tr></thead>")
                    for datagroup in service:
                        internalf.write("<tr>\n")  # Open row
                        internalf.write("<td>" + datagroup[0] + "</td>\n")  # Name of Account
                        internalf.write("<td>" + datagroup[1] + "<td>\n")  # Full description
                        internalf.write("<td>" + datagroup[2] + "</td>\n")  # Admin y/n
                        internalf.write("</tr>\n")  # Close row
                    internalf.write("</table>\n")  # End table
                    infoappend("Service", "/" + sys + "HCP_Service_Accounts_", internalf)
                    internalf.close()
                else:
                    print("Too many files processed!")

command = requestinfo()
currentUrl = 0
while currentUrl < 4:
    # Initial setup
    if currentUrl == 0:
        # Dummy urls to satisfy requests
        trueUrl = "https://baseurl"
        secondaryUrl = "https://base/login/login.jsp"
        currentUrl = currentUrl + 1
        print("Completed preliminary connection check")
    elif currentUrl == 1:
        trueUrl = "https://baseurl"
        secondaryUrl = "https://base/login/login.jsp"

        # output files
        adminfile = fileinfo.prefix + "HCP/DC1Hcp01_(IP ADDRESS)/Human_Admin/DC1HCP_Admin_Audit_" + str(fileinfo.currentdate) + ".html"
        nonadminfile = fileinfo.prefix + "HCP/DC1Hcp01_(IP ADDRESS)/Human_Non_Admin/DC1HCP_Non-Admin_Audit_" + str(fileinfo.currentdate) + ".html"
        servicefile = fileinfo.prefix + "HCP/DC1Hcp01_(IP ADDRESS)/Service/DC1HCP_Service_Accounts_" + str(fileinfo.currentdate) + ".html"
        tenantfile = fileinfo.prefix + "HCP/DC1Hcp01_(IP ADDRESS)/Tenants/DC1HCP_Tenants_" + str(fileinfo.currentdate) + ".html"
        filelist = [adminfile, nonadminfile, tenantfile, servicefile]

        tenantlist = command.call(trueUrl, secondaryUrl, adminfile, nonadminfile, servicefile)

        userlist = command.processuser(command.cookieVal)
        writehtml(filelist, "DC1Hcp01_(IP ADDRESS)", tenantlist, userlist[0], userlist[1], userlist[2], "DC1")
        currentUrl = currentUrl + 1
        print("Completed DC1")

    elif currentUrl == 2:
        trueUrl = "https://baseurl"
        secondaryUrl = "https://base/login/login.jsp"
        # output files
        adminfile = fileinfo.prefix + "HCP/DC2Hcp01_(IP ADDRESS)/Human_Admin/DC2HCP_Admin_Audit_" + str(
            fileinfo.currentdate) + ".html"
        nonadminfile = fileinfo.prefix + "HCP/DC2Hcp01_(IP ADDRESS)/Human_Non_Admin/DC2HCP_Non-Admin_Audit_" + str(
            fileinfo.currentdate) + ".html"
        servicefile = fileinfo.prefix + "HCP/DC2Hcp01_(IP ADDRESS)/Service/DC2HCP_Service_Accounts_" + str(
            fileinfo.currentdate) + ".html"
        tenantfile = fileinfo.prefix + "HCP/DC2Hcp01_(IP ADDRESS)/Tenants/DC2HCP_Tenants_" + str(
            fileinfo.currentdate) + ".html"
        filelist = [adminfile, nonadminfile, tenantfile, servicefile]

        tenantlist = command.call(trueUrl, secondaryUrl, adminfile, nonadminfile, servicefile)

        userlist = command.processuser(command.cookieVal)
        writehtml(filelist, "DC2Hcp01_(IP ADDRESS)", tenantlist, userlist[0], userlist[1], userlist[2], "DC2")
        currentUrl = currentUrl + 1
        print("Completed DC2")

    elif currentUrl == 3:
        trueUrl = "https://baseurl"
        secondaryUrl = "https://base/login/login.jsp"
        # output files
        adminfile = fileinfo.prefix + "HCP/DC3Hcp01_(IP ADDRESS)/Human_Admin/DC3HCP_Admin_Audit_" + str(
            fileinfo.currentdate) + ".html"
        nonadminfile = fileinfo.prefix + "HCP/DC3Hcp01_(IP ADDRESS)/Human_Non_Admin/DC3HCP_Non-Admin_Audit_" + str(
            fileinfo.currentdate) + ".html"
        servicefile = fileinfo.prefix + "HCP/DC3Hcp01_(IP ADDRESS)/Service/DC3HCP_Service_Accounts_" + str(
            fileinfo.currentdate) + ".html"
        tenantfile = fileinfo.prefix + "HCP/DC3Hcp01_(IP ADDRESS)/Tenants/DC3HCP_Tenants_" + str(
            fileinfo.currentdate) + ".html"
        filelist = [adminfile, nonadminfile, tenantfile, servicefile]

        tenantlist = command.call(trueUrl, secondaryUrl, adminfile, nonadminfile, servicefile)

        userlist = command.processuser(command.cookieVal)
        writehtml(filelist, "DC3Hcp01_(IP ADDRESS)", tenantlist, userlist[0], userlist[1], userlist[2], "DC3")
        currentUrl = currentUrl + 1
        print("Completed DC3")
