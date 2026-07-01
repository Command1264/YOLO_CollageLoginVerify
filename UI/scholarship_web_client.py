from __future__ import annotations

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from collageLogin.CYUTScholarships import CYUTScholarships


class ScholarshipWebClient:
    """Web gateway for CYUT scholarship pages and semester switching."""

    def request_dataset_page(
        self,
        client: CYUTScholarships,
        path: str,
        semester_value: str | None,
    ) -> requests.Response:
        """Request a dataset page and try to switch semester when needed.

        Args:
            client (CYUTScholarships): Logged-in client instance.
            path (str): Dataset path under system domain.
            semester_value (str | None): Target semester value.

        Returns:
            requests.Response: Final page response.
        """
        url = f"{client.system_domain}{path}"
        session = requests.Session()
        session.headers.update(client.headers)
        session.cookies.update(client.cookies)

        initial_response = session.get(
            url,
            allow_redirects=False,
            timeout=25,
        )
        if not semester_value or initial_response.status_code != 200:
            client.cookies.update(session.cookies.get_dict())
            return initial_response

        initial_selected = self._extract_selected_semester(initial_response.text)
        if initial_selected == semester_value:
            client.cookies.update(session.cookies.get_dict())
            return initial_response

        soup = BeautifulSoup(initial_response.text, "html.parser")
        post_payload = self._build_semester_form_payload(soup, semester_value)
        post_url = self._resolve_semester_post_url(soup, url)
        if len(post_payload) != 0:
            post_response = session.post(
                post_url,
                headers={
                    **client.headers,
                    "Referer": url,
                },
                data=post_payload,
                allow_redirects=False,
                timeout=25,
            )
            if post_response.status_code == 200:
                selected_after_post = self._extract_selected_semester(post_response.text)
                if selected_after_post is None or selected_after_post == semester_value:
                    client.cookies.update(session.cookies.get_dict())
                    return post_response

        fallback_get_response = session.get(
            url,
            params={"acy": semester_value},
            allow_redirects=False,
            timeout=25,
        )
        client.cookies.update(session.cookies.get_dict())
        return fallback_get_response

    def get_default_semester(self, client: CYUTScholarships) -> str | None:
        """Read current selected semester from ST0075 page.

        Args:
            client (CYUTScholarships): Logged-in client instance.

        Returns:
            str | None: Selected semester value if available.
        """
        response = requests.get(
            f"{client.system_domain}/ST0075/",
            headers=client.headers,
            cookies=client.cookies,
            allow_redirects=False,
            timeout=20,
        )
        if response.status_code != 200:
            return None
        soup = BeautifulSoup(response.text, "html.parser")
        option = soup.select_one("select#acy option[selected]")
        if option is None:
            return None
        return str(option.get("value", "")).strip() or None

    def get_semester_page(self, client: CYUTScholarships) -> requests.Response:
        """Fetch semester listing page.

        Args:
            client (CYUTScholarships): Logged-in client instance.

        Returns:
            requests.Response: ST0075 page response.
        """
        return requests.get(
            f"{client.system_domain}/ST0075/",
            headers=client.headers,
            cookies=client.cookies,
            allow_redirects=False,
            timeout=20,
        )

    def _extract_selected_semester(self, html_text: str) -> str | None:
        soup = BeautifulSoup(html_text, "html.parser")
        selected_option = soup.select_one("select#acy option[selected]")
        if selected_option is None:
            select_node = soup.select_one("select#acy")
            if select_node is None:
                return None
            first_option = select_node.select_one("option")
            if first_option is None:
                return None
            first_value = first_option.get("value", "")
            return str(first_value).strip() or None
        value = selected_option.get("value", "")
        return str(value).strip() or None

    def _build_semester_form_payload(
        self,
        soup: BeautifulSoup,
        semester_value: str,
    ) -> list[tuple[str, str]]:
        select_node = soup.select_one("select#acy")
        form_node = select_node.find_parent("form") if select_node is not None else None
        if form_node is None:
            token_input = soup.select_one("form input[name='__RequestVerificationToken']")
            if token_input is not None:
                form_node = token_input.find_parent("form")
        if form_node is None:
            form_node = soup.select_one("form")
        if form_node is None:
            return [("acy", semester_value)]

        payload: list[tuple[str, str]] = []
        for input_node in form_node.select("input[name]"):
            name = str(input_node.get("name", "")).strip()
            if name == "":
                continue
            input_type = str(input_node.get("type", "text")).strip().lower()
            value = str(input_node.get("value", ""))
            if input_type in {"checkbox", "radio"} and (not input_node.has_attr("checked")):
                continue
            payload.append((name, value))

        for select in form_node.select("select[name]"):
            name = str(select.get("name", "")).strip()
            if name == "":
                continue
            selected_option = select.select_one("option[selected]")
            if selected_option is None:
                selected_option = select.select_one("option")
            value = "" if selected_option is None else str(selected_option.get("value", ""))
            payload.append((name, value))

        filtered_payload = [item for item in payload if item[0] != "acy"]
        filtered_payload.append(("acy", semester_value))
        return filtered_payload

    def _resolve_semester_post_url(self, soup: BeautifulSoup, default_url: str) -> str:
        select_node = soup.select_one("select#acy")
        form_node = select_node.find_parent("form") if select_node is not None else None
        if form_node is None:
            token_input = soup.select_one("form input[name='__RequestVerificationToken']")
            if token_input is not None:
                form_node = token_input.find_parent("form")
        if form_node is None:
            return default_url.rstrip("/")
        action_value = str(form_node.get("action", "")).strip()
        if action_value == "":
            return default_url.rstrip("/")
        return urljoin(default_url, action_value)
