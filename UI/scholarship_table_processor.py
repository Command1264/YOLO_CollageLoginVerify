from __future__ import annotations

import datetime
import re
from io import StringIO

import pandas as pd


class ScholarshipTableProcessor:
    """Table preprocessing and normalization helper for scholarship datasets."""

    def safe_read_table_df(self, table_node) -> pd.DataFrame:
        """Parse an HTML table node into DataFrame with safe fallbacks.

        Args:
            table_node: BeautifulSoup table-like node.

        Returns:
            pd.DataFrame: Parsed table data.
        """
        headers = self.extract_table_headers(table_node)
        try:
            table_list = pd.read_html(StringIO(str(table_node)))
        except ValueError:
            table_list = []
        if len(table_list) == 0:
            if len(headers) != 0:
                return pd.DataFrame(columns=headers)
            return pd.DataFrame(columns=["無資料"])
        table_df = table_list[0].copy()
        if table_df.shape[1] == 0:
            if len(headers) != 0:
                return pd.DataFrame(columns=headers)
            return pd.DataFrame(columns=["無資料"])
        return table_df

    def extract_table_headers(self, table_node) -> list[str]:
        """Extract best-effort headers from an HTML table node.

        Args:
            table_node: BeautifulSoup table-like node.

        Returns:
            list[str]: Header names.
        """
        headers = [item.get_text(strip=True) for item in table_node.select("thead th")]
        if len(headers) != 0:
            return headers
        first_row = table_node.select_one("tr")
        if first_row is None:
            return []
        row_headers = [item.get_text(strip=True) for item in first_row.select("th")]
        if len(row_headers) != 0:
            return row_headers
        return [item.get_text(strip=True) for item in first_row.select("td")]

    def normalize_df(self, table_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize DataFrame values and column labels.

        Args:
            table_df (pd.DataFrame): Source table.

        Returns:
            pd.DataFrame: Normalized table.
        """
        table_df = table_df.copy()
        table_df = table_df.fillna("")
        table_df.columns = [str(column).strip() for column in table_df.columns]
        for column in table_df.columns:
            table_df[column] = table_df[column].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()
        return table_df

    def preprocess_internal_external_table(self, table_df: pd.DataFrame, soup) -> pd.DataFrame:
        """Apply dataset-specific transform for internal/external scholarships.

        Args:
            table_df (pd.DataFrame): Source table.
            soup: Page soup containing detail rows.

        Returns:
            pd.DataFrame: Processed table.
        """
        result_df = table_df.copy()
        result_df = result_df.drop(columns=["Unnamed: 0", "名額"], errors="ignore")

        if "外部連結" not in result_df.columns:
            insert_at = min(4, result_df.shape[1])
            result_df.insert(insert_at, "外部連結", "LINK")

        if "類型" in result_df.columns:
            result_df["類型"] = result_df["類型"].replace({
                "校外自行申請": "自申",
                "校外學校彙整": "校彙",
            })
        if "金額" in result_df.columns:
            result_df["金額"] = result_df["金額"].replace({"待確定": "0"})
            result_df["金額"] = result_df["金額"].apply(self.format_amount_value)
        if "申請期限" in result_df.columns:
            result_df["申請期限"] = result_df["申請期限"].apply(self.format_deadline_value)

        name_column = "編號-獎學金名稱"
        if name_column in result_df.columns:
            result_df = result_df.sort_values(by=name_column, ascending=True).reset_index(drop=True)
            for idx, name in enumerate(result_df[name_column].tolist()):
                split_name = str(name).split("-", 1)
                if len(split_name) != 2:
                    continue
                row_id = split_name[0].strip()
                detail_node = soup.select_one(f"#tr_{row_id}")
                if detail_node is None:
                    continue
                try:
                    detail_df_list = pd.read_html(StringIO(str(detail_node)))
                except ValueError:
                    detail_df_list = []
                if len(detail_df_list) != 1:
                    continue
                detail_df = detail_df_list[0]
                try:
                    link_df = detail_df.iloc[8:10, 0:2].dropna()
                except Exception:
                    continue
                if link_df.shape[0] == 0:
                    continue
                relation_links = self.extract_relation_links(link_df)
                file_link = relation_links.get("相關檔案")
                external_link = relation_links.get("相關網址")

                if file_link:
                    result_df.at[idx, name_column] = f'=HYPERLINK("{file_link}", "{name}")'
                if external_link:
                    result_df.at[idx, "外部連結"] = f'=HYPERLINK("{external_link}", "LINK")'
        return result_df

    def preprocess_apply_table(self, table_df: pd.DataFrame) -> pd.DataFrame:
        """Apply dataset-specific transform for apply-result table."""
        result_df = table_df.copy()
        if "獲獎金額" in result_df.columns:
            result_df["獲獎金額"] = result_df["獲獎金額"].fillna("0")
            result_df["獲獎金額"] = result_df["獲獎金額"].replace({"": "0", "nan": "0"})
            result_df["獲獎金額"] = result_df["獲獎金額"].apply(self.format_amount_value)
        if "申請項目" in result_df.columns:
            result_df = result_df.sort_values(by="申請項目", ascending=True).reset_index(drop=True)
        return result_df

    def extract_relation_links(self, link_df: pd.DataFrame) -> dict[str, str]:
        """Extract related file/url links from detail table."""
        relation_links: dict[str, str] = {}
        for _, row in link_df.iterrows():
            key = str(row.iloc[0]).strip()
            value = str(row.iloc[1]).strip()
            if key == "" or value == "" or value.lower() == "nan":
                continue
            if "相關檔案" in key and "相關檔案" not in relation_links:
                relation_links["相關檔案"] = value
            elif "相關網址" in key and "相關網址" not in relation_links:
                relation_links["相關網址"] = value

        if ("相關檔案" not in relation_links) and (link_df.shape[0] >= 1):
            first_link = str(link_df.iloc[0, 1]).strip()
            if first_link != "" and first_link.lower() != "nan":
                relation_links["相關檔案"] = first_link
        if ("相關網址" not in relation_links) and (link_df.shape[0] >= 2):
            second_link = str(link_df.iloc[1, 1]).strip()
            if second_link != "" and second_link.lower() != "nan":
                relation_links["相關網址"] = second_link
        return relation_links

    def format_deadline_value(self, value) -> str:
        """Normalize date-like text to yyyy/MM/dd when possible."""
        text = str(value).strip()
        if text == "" or text.lower() == "nan":
            return ""
        match = re.search(r"(\d{4})[./-](\d{1,2})[./-](\d{1,2})", text)
        if match is None:
            return text.replace("-", "/")
        year = int(match.group(1))
        month = int(match.group(2))
        day = int(match.group(3))
        return f"{year:04d}/{month:02d}/{day:02d}"

    def format_amount_value(self, value) -> str:
        """Normalize amount-like text to grouped integer string."""
        text = str(value).strip()
        if text == "" or text.lower() == "nan":
            return "0"
        cleaned = text.replace(",", "")
        cleaned = re.sub(r"[^\d\-.]", "", cleaned)
        if cleaned in {"", "-", ".", "-."}:
            return "0"
        try:
            amount = int(float(cleaned))
        except ValueError:
            return text
        return f"{amount:,}"

    def df_to_lines(self, table_df: pd.DataFrame) -> list[str]:
        """Convert DataFrame to header/body lines for diff/hash."""
        if table_df is None or table_df.shape[1] == 0:
            return []
        header = "|".join([str(item).strip() for item in table_df.columns.tolist()])
        body = [
            "|".join([str(item).strip() for item in row.tolist()])
            for _, row in table_df.iterrows()
        ]
        return [header] + body

    def normalize_cloud_df(self, table_df: pd.DataFrame) -> pd.DataFrame:
        """Normalize cloud table values for stable comparison."""
        result_df = table_df.copy()
        if "申請期限" in result_df.columns:
            def _convert_excel_date(value) -> str:
                text = str(value).strip()
                if text == "" or text.lower() == "nan":
                    return ""
                try:
                    number = float(text)
                    date_value = datetime.datetime(1900, 1, 1) + datetime.timedelta(days=number - 2)
                    return date_value.strftime("%Y/%m/%d")
                except Exception:
                    return self.format_deadline_value(text)

            result_df["申請期限"] = result_df["申請期限"].apply(_convert_excel_date)
        if "金額" in result_df.columns:
            result_df["金額"] = result_df["金額"].apply(self.format_amount_value)
        if "獲獎金額" in result_df.columns:
            result_df["獲獎金額"] = result_df["獲獎金額"].apply(self.format_amount_value)
        return result_df
