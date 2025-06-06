from dataclasses import dataclass


@dataclass
class Repository:
	owner: str
	name: str
	url: str
	html_url: str
	description: str | None = None

	@classmethod
	def from_dict(cls, data: dict) -> "Repository":
		return cls(
			owner=data["owner"]["login"],
			name=data["name"],
			url=data["url"],
			html_url=data["html_url"],
			description=data.get("description"),
		)
