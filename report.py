import requests
from msauth import MSAuth

class UnauthorizedException(Exception):
    pass

class Report:
    def __init__(self, config, idf_cookies, ms_cookies):
        self.session = requests.session()
        self.config = config
        self.msauth = MSAuth(config['id_num'], config['microsoft_passwd'], idf_cookies, ms_cookies)
        self._set_idf_cookies(idf_cookies)
    
    def _set_idf_cookies(self, idf_cookies):
        for cookie in idf_cookies:
            self.session.cookies.set(**{key: cookie[key] for key in ['name', 'value', 'domain', 'path']})

    def login(self, otp_callback):
        idf_cookies, ms_cookies = self.msauth.login(otp_callback)
        self._set_idf_cookies(idf_cookies)

        burp0_url = "https://one.prat.idf.il/api/account/loginCommander"
        burp0_json={"password": self.config["commander_passwd"], "recaptchaValue": None, "username": self.config["id_num"]}
        response = self.session.post(burp0_url, json=burp0_json)

        burp0_url = "https://one.prat.idf.il/api/account/getUser"
        response = self.session.get(burp0_url)

        if response.status_code == 401:
            raise UnauthorizedException()

        if not response.json().get('isCommanderAuth', False):
            raise Exception()

        return idf_cookies, ms_cookies

    def get_soldiers(self):
        burp2_url = "https://one.prat.idf.il/api/attendance/GetGroups?groupcode="
        burp2_headers = {"authority": "one.prat.idf.il", "access-control-allow-origin": "*", "accept": "application/json, text/plain, */*", "sec-ch-ua-mobile": "?0", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.123 Safari/537.36", "pragma": "no-cache", "crossdomain": "true", "sec-ch-ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"91\", \"Chromium\";v=\"91\"", "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://one.prat.idf.il/commander", "accept-language": "he,en-US;q=0.9,en;q=0.8,he-IL;q=0.7"}
        response = self.session.get(burp2_url, headers=burp2_headers)

        if response.status_code == 401:
            raise UnauthorizedException()

        return response.json()['firstGroup']['users']

    def do_report_and_get_statuses(self, users, pre_placements=None):
        burp0_headers = {"authority": "one.prat.idf.il", "access-control-allow-origin": "*", "accept": "application/json, text/plain, */*", "sec-ch-ua-mobile": "?0", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.123 Safari/537.36", "pragma": "no-cache", "crossdomain": "true", "sec-ch-ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"91\", \"Chromium\";v=\"91\"", "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://one.prat.idf.il/commander/otherStatus", "accept-language": "he,en-US;q=0.9,en;q=0.8,he-IL;q=0.7", "Origin": "https://one.prat.idf.il"}    
        for user in users:
            main_status_code = "01"
            secondary_status_code = "01"
            note = None
            if pre_placements is not None and user['mi'] in pre_placements:
                main_status_code = pre_placements[user['mi']]['mainStatusCode']
                secondary_status_code = pre_placements[user['mi']]['secondaryStatusCode']
                if 'note' in pre_placements[user['mi']].keys():
                    note = pre_placements[user['mi']]['note']

            burp1_url = "https://one.prat.idf.il/api/Attendance/GetStatusesForCommander"
            burp1_headers = {"authority": "one.prat.idf.il", "access-control-allow-origin": "*", "accept": "application/json, text/plain, */*", "sec-ch-ua-mobile": "?0", "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.123 Safari/537.36", "pragma": "no-cache", "crossdomain": "true", "sec-ch-ua": "\" Not;A Brand\";v=\"99\", \"Google Chrome\";v=\"91\", \"Chromium\";v=\"91\"", "sec-fetch-site": "same-origin", "sec-fetch-mode": "cors", "sec-fetch-dest": "empty", "referer": "https://one.prat.idf.il/commander/otherStatus", "accept-language": "he,en-US;q=0.9,en;q=0.8,he-IL;q=0.7", "Origin": "https://one.prat.idf.il"}
            burp1_json={"groupCode": user['groupCode'], "pratMi": user['mi']}
            resp1 = self.session.post(burp1_url, headers=burp1_headers, json=burp1_json)
            if resp1.status_code == 401:
                raise UnauthorizedException()

            burp0_url = "https://one.prat.idf.il/api/Attendance/updateAndSendPrat"
            burp0_json={"groupCode": user['groupCode'], "mainStatusCode": main_status_code, "mi": user['mi'], "note": note, "secondaryStatusCode": secondary_status_code}
            resp2 = self.session.post(burp0_url, headers=burp0_headers, json=burp0_json)
            if resp2.status_code == 401:
                raise UnauthorizedException()

        # get statuses from server
        burp0_url = "https://one.prat.idf.il/api/Attendance/GetGroups"
        r = self.session.get(burp0_url, headers=burp0_headers)
        if r.status_code == 401:
            raise UnauthorizedException()

        if not r.ok:
            return "Could not get group for confirmation!"

        group = r.json()

        final = ""
        for user in group['firstGroup']['users']:
            name = "{} {}".format(user['firstName'], user['lastName'])
            status = "{} {}".format(user['approvedMainName'], user['approvedSecondaryName'])
            note = user['note'] if user['note'] else ''
            final = final + "{name}   -   {status} {note}\n".format(name=name, status=status, note=note)

        return final