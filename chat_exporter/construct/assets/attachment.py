import base64
import math

from chat_exporter.ext.discord_utils import DiscordUtils
from chat_exporter.ext.html_generator import (
    fill_out,
    img_attachment,
    msg_attachment,
    audio_attachment,
    video_attachment,
    PARSE_MODE_NONE,
)


class Attachment:
    def __init__(self, attachments, guild):
        self.attachments = attachments
        self.guild = guild

    async def flow(self):
        await self.build_attachment()
        return self.attachments

    async def build_attachment(self):
        if self.attachments.content_type is not None:
            if "image" in self.attachments.content_type:
                return await self.image()
            elif "video" in self.attachments.content_type:
                return await self.video()
            elif "audio" in self.attachments.content_type:
                return await self.audio()
        await self.file()

    async def image(self):
        image_data = await self.attachments.read()
        self.attachments.proxy_url = f"data:{self.attachments.content_type};base64,{base64.b64encode(image_data).decode('utf-8')}"
        self.attachments.filename = self.attachments.filename if self.attachments.filename else "image.png"
        self.attachments.size = len(image_data)
        size_kb = self.attachments.size / 1024
        size_mb = size_kb / 1024
        self.attachments.size = f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_mb:.2f} MB"
        self.attachments.width = self.attachments.width if hasattr(self.attachments, 'width') else 720
        self.attachments.height = self.attachments.height if hasattr(self.attachments, 'height') else 480

        self.attachments = await fill_out(
            self.guild, img_attachment, [
                ("ATTACH_URL", str(self.attachments.proxy_url), PARSE_MODE_NONE),
                ("ATTACH_URL_THUMB", str(self.attachments.proxy_url), PARSE_MODE_NONE),
                ("ATTACH_NAME", str(self.attachments.filename), PARSE_MODE_NONE),
                ("ATTACH_SIZE", str(self.attachments.size), PARSE_MODE_NONE),
                ("ATTACH_WIDTH", str(self.attachments.width), PARSE_MODE_NONE),
                ("ATTACH_HEIGHT", str(self.attachments.height), PARSE_MODE_NONE),
            ]
        )

    async def video(self):
        # If the video is more than 10MB, do not embed as base64, use the original URL
        if hasattr(self.attachments, 'size') and self.attachments.size > 10 * 1024 * 1024:
            self.attachments.proxy_url = getattr(self.attachments, 'url', None) or getattr(self.attachments, 'proxy_url', None)
        else:
            self.attachments.proxy_url = self.make_data_uri(
                self.attachments.content_type,
                await self.attachments.read()
            )

        self.attachments = await fill_out(self.guild, video_attachment, [
            ("ATTACH_URL", self.attachments.proxy_url, PARSE_MODE_NONE),
        ])

    async def audio(self):
        file_icon = DiscordUtils.file_attachment_audio
        file_size = self.get_file_size(self.attachments.size)
        self.attachments.proxy_url = self.make_data_uri(
            self.attachments.content_type,
            await self.attachments.read()
        )


        self.attachments = await fill_out(self.guild, audio_attachment, [
            ("ATTACH_ICON", file_icon, PARSE_MODE_NONE),
            ("ATTACH_URL", self.attachments.proxy_url, PARSE_MODE_NONE),
            ("ATTACH_BYTES", str(file_size), PARSE_MODE_NONE),
            ("ATTACH_AUDIO", self.attachments.proxy_url, PARSE_MODE_NONE),
            ("ATTACH_FILE", str(self.attachments.filename), PARSE_MODE_NONE)
        ])

    async def file(self):
        file_icon = await self.get_file_icon()
        # If the file is more than 10mb, we will not read it into memory
        if not self.attachments.size > 10 * 1024 * 1024:
            self.attachments.proxy_url = self.make_data_uri(
                self.attachments.content_type,
                await self.attachments.read()
            )

        file_size = self.get_file_size(self.attachments.size)

        self.attachments = await fill_out(self.guild, msg_attachment, [
            ("ATTACH_ICON", file_icon, PARSE_MODE_NONE),
            ("ATTACH_URL", self.attachments.proxy_url, PARSE_MODE_NONE),
            ("ATTACH_BYTES", str(file_size), PARSE_MODE_NONE),
            ("ATTACH_FILE", str(self.attachments.filename), PARSE_MODE_NONE)
        ])

    @staticmethod
    def get_file_size(file_size):
        if file_size == 0:
            return "0 bytes"
        size_name = ("bytes", "KB", "MB")
        i = int(math.floor(math.log(file_size, 1024)))
        p = math.pow(1024, i)
        s = round(file_size / p, 2)
        return "%s %s" % (s, size_name[i])

    async def get_file_icon(self) -> str:
        acrobat_types = "pdf"
        webcode_types = "html", "htm", "css", "rss", "xhtml", "xml"
        code_types = "py", "cgi", "pl", "gadget", "jar", "msi", "wsf", "bat", "php", "js"
        document_types = (
            "txt", "doc", "docx", "rtf", "xls", "xlsx", "ppt", "pptx", "odt", "odp", "ods", "odg", "odf", "swx",
            "sxi", "sxc", "sxd", "stw"
        )
        archive_types = (
            "br", "rpm", "dcm", "epub", "zip", "tar", "rar", "gz", "bz2", "7x", "deb", "ar", "Z", "lzo", "lz", "lz4",
            "arj", "pkg", "z"
        )

        for tmp in [self.attachments.proxy_url, self.attachments.filename]:
            if not tmp:
                continue
            extension = tmp.rsplit('.', 1)[-1]
            if extension in acrobat_types:
                return DiscordUtils.file_attachment_acrobat
            elif extension in webcode_types:
                return DiscordUtils.file_attachment_webcode
            elif extension in code_types:
                return DiscordUtils.file_attachment_code
            elif extension in document_types:
                return DiscordUtils.file_attachment_document
            elif extension in archive_types:
                return DiscordUtils.file_attachment_archive
        
        return DiscordUtils.file_attachment_unknown
    
    @staticmethod
    def make_data_uri(content_type: str, binary: bytes) -> str:
        safe_type = content_type.strip().split(";")[0]
        
        if safe_type.startswith("text/"):
            safe_type += ";charset=utf-8"

        base64_data = base64.b64encode(binary).decode('utf-8')
        return f"data:{safe_type};base64,{base64_data}"

