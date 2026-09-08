import base64
import logging
from xml.sax.saxutils import escape

import requests


logger = logging.getLogger(__name__)


class WorkdayEIBService:
    """
    Launch an uploaded EIB file through Workday's Launch_EIB_Request SOAP API.

    Authentication:
        WS-Security UsernameToken / PasswordText

    The uploaded file is:
        SQLite BLOB
            -> bytes
            -> Base64
            -> SOAP Attachment_Data
            -> Workday
    """

    WSSE_NAMESPACE = (
        "http://docs.oasis-open.org/wss/2004/01/"
        "oasis-200401-wss-wssecurity-secext-1.0.xsd"
    )

    WSU_NAMESPACE = (
        "http://docs.oasis-open.org/wss/2004/01/"
        "oasis-200401-wss-wssecurity-utility-1.0.xsd"
    )

    PASSWORD_TEXT_TYPE = (
        "http://docs.oasis-open.org/wss/2004/01/"
        "oasis-200401-wss-username-token-profile-1.0#PasswordText"
    )

    @classmethod
    def build_launch_request(
        cls,
        *,
        base64_content: str,
        integration_system_id: str,
        filename: str,
        content_type: str,
        username: str,
        password: str,
    ) -> str:
        """
        Build the complete SOAP envelope.

        IMPORTANT:
        Credentials are deliberately placed in the WS-Security SOAP header,
        not in HTTP Basic Authentication.
        """

        safe_username = escape(username)
        safe_password = escape(password)
        safe_integration_id = escape(integration_system_id)
        safe_filename = escape(filename)

        safe_content_type = escape(
            content_type
            or (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )
        )

        soap = f"""<soapenv:Envelope xmlns:bsvc="urn:com.workday/bsvc" xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
    <soapenv:Header>
        <wsse:Security soapenv:mustUnderstand="1" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <wsse:UsernameToken>
                <wsse:Username>uyoga@tcs_dpt2</wsse:Username>
                <wsse:Password Type="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordText">Workday@12345</wsse:Password>
            </wsse:UsernameToken>
        </wsse:Security>
    </soapenv:Header>
    <soapenv:Body>
        <wd:Launch_EIB_Request xmlns:wd="urn:com.workday/bsvc" wd:version="v47.0">
            <wd:Integration_System_Reference>
                <wd:ID wd:type="Integration_System_ID">InboundEIBCreateCostCenter</wd:ID>
            </wd:Integration_System_Reference>
            <wd:Service_Component_Data>
                <wd:Data_Source>true</wd:Data_Source>
                <wd:Field_Override_Data>
                    <wd:Field_Name>Integration Attachment</wd:Field_Name>
                    <wd:Attachment_Data wd:Content_Type="text/xml;charset=UTF-8" wd:Filename={filename} wd:Encoding="base64" wd:Compressed="true">
                        <wd:File_ID>{filename}</wd:File_ID>
                        <wd:File_Content>
                        {base64_content}
                        </wd:File_Content>
                        <wd:Comments>string</wd:Comments>
                    </wd:Attachment_Data>
                </wd:Field_Override_Data>
            </wd:Service_Component_Data>
        </wd:Launch_EIB_Request>
    </soapenv:Body>
</soapenv:Envelope>
"""

        print("Soap is =======")
        print()

        return soap

    @classmethod
    def launch(
        cls,
        *,
        file_content: bytes,
        filename: str,
        content_type: str,
        endpoint: str,
        username: str,
        password: str,
        integration_system_id: str,
    ) -> dict:
        """
        Launch the uploaded EIB file in Workday.
        """

        # ---------------------------------------------------------
        # STEP 20
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 20] Workday service entered",
            flush=True,
        )

        # ---------------------------------------------------------
        # STEP 21
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 21] Workday configuration check | "
            f"endpoint_configured={bool(endpoint)} | "
            f"username_configured={bool(username)} | "
            f"password_configured={bool(password)} | "
            f"integration_id={integration_system_id}",
            flush=True,
        )

        if not endpoint:
            raise ValueError(
                "WD_DEFAULT_ENDPOINT is not configured."
            )

        if not username:
            raise ValueError(
                "WD_DEFAULT_USERNAME is not configured."
            )

        if not password:
            raise ValueError(
                "WD_DEFAULT_PASSWORD is not configured."
            )

        if not integration_system_id:
            raise ValueError(
                "Workday integration system ID is not configured."
            )

        # ---------------------------------------------------------
        # STEP 22
        # ---------------------------------------------------------
        file_size = len(file_content or b"")

        print(
            "[EIB DEBUG 22] File received by Workday service | "
            f"filename={filename} | "
            f"content_type={content_type} | "
            f"size_bytes={file_size}",
            flush=True,
        )

        if not file_content:
            print(
                "[EIB DEBUG ERROR] Uploaded file is empty",
                flush=True,
            )

            raise ValueError(
                "The uploaded EIB file is empty."
            )

        # ---------------------------------------------------------
        # STEP 23
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 23] Base64 encoding uploaded file",
            flush=True,
        )

        encoded = base64.b64encode(file_content).decode("utf-8")

        # ---------------------------------------------------------
        # STEP 24
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 24] Base64 encoding complete | "
            f"encoded_length={len(encoded)}",
            flush=True,
        )

        # ---------------------------------------------------------
        # STEP 25
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 25] Building Workday SOAP "
            "Launch_EIB_Request",
            flush=True,
        )

        soap = cls.build_launch_request(
            base64_content=encoded,
            integration_system_id=integration_system_id,
            filename=filename,
            content_type=content_type,
            username=username,
            password=password,
        )

        # ---------------------------------------------------------
        # STEP 26
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 26] SOAP request built | "
            f"request_length={len(soap)} | "
            "authentication=WS_SECURITY_USERNAME_TOKEN",
            flush=True,
        )

        # SECURITY:
        # Never print the complete SOAP payload because it contains:
        #   - password
        #   - entire Base64 encoded Excel file

        # ---------------------------------------------------------
        # STEP 27
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 27] Sending POST to Workday | "
            f"endpoint={endpoint} | "
            "authentication=WS_SECURITY_USERNAME_TOKEN",
            flush=True,
        )

        try:
            response = requests.post(
                endpoint,
                data=soap.encode("utf-8"),
                headers={
                    "Content-Type": "text/xml;charset=UTF-8",
                    "SOAPAction": "",
                },
                timeout=60,
                verify=True,
            )

        except requests.exceptions.Timeout as exc:

            print(
                "[EIB DEBUG ERROR] Workday request timed out | "
                f"error={exc}",
                flush=True,
            )

            raise RuntimeError(
                f"Workday request timed out: {exc}"
            ) from exc

        except requests.exceptions.SSLError as exc:

            print(
                "[EIB DEBUG ERROR] Workday SSL error | "
                f"error={exc}",
                flush=True,
            )

            raise RuntimeError(
                f"Workday SSL/TLS error: {exc}"
            ) from exc

        except requests.exceptions.ConnectionError as exc:

            print(
                "[EIB DEBUG ERROR] Workday connection error | "
                f"error={exc}",
                flush=True,
            )

            raise RuntimeError(
                f"Could not connect to Workday: {exc}"
            ) from exc

        except requests.exceptions.RequestException as exc:

            print(
                "[EIB DEBUG ERROR] Workday HTTP request error | "
                f"error={exc}",
                flush=True,
            )

            raise RuntimeError(
                f"Workday HTTP request failed: {exc}"
            ) from exc

        # ---------------------------------------------------------
        # STEP 28
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 28] Workday response received | "
            f"status_code={response.status_code} | "
            f"response_length={len(response.text)} | "
            f"content_type="
            f"{response.headers.get('content-type')}",
            flush=True,
        )

        # ---------------------------------------------------------
        # STEP 29
        # ---------------------------------------------------------
        response_preview = (
            response.text[:3000]
            .replace("\n", " ")
            .replace("\r", " ")
        )

        print(
            "[EIB DEBUG 29] Workday response preview | "
            f"{response_preview}",
            flush=True,
        )

        # ---------------------------------------------------------
        # STEP 30
        # ---------------------------------------------------------
        response_lower = response.text.lower()

        soap_fault = (
            "<soap-env:fault" in response_lower
            or "<soap-env:fault" in response_lower
            or "<soap:Fault" in response_lower
            or ":fault>" in response_lower
            or "<faultcode>" in response_lower
        )

        print(
            "[EIB DEBUG 30] Workday response validation | "
            f"http_error={response.status_code >= 400} | "
            f"soap_fault={soap_fault}",
            flush=True,
        )

        if response.status_code >= 400 or soap_fault:

            logger.error(
                "Workday EIB launch failed: HTTP %s",
                response.status_code,
            )

            print(
                "[EIB DEBUG ERROR] Workday rejected the EIB launch",
                flush=True,
            )

            raise RuntimeError(
                "Workday rejected the EIB launch "
                f"(HTTP {response.status_code}). "
                f"Response: {response_preview}"
            )

        # ---------------------------------------------------------
        # STEP 31
        # ---------------------------------------------------------
        print(
            "[EIB DEBUG 31] Workday accepted the EIB launch request",
            flush=True,
        )

        return {
            "status": "SUCCESS",
            "status_code": response.status_code,
            "message": (
                "Cost Center EIB launch request accepted by Workday."
            ),
        }