from dataclasses import dataclass


@dataclass
class Issue:
	title: str
	body: str

	@classmethod
	def from_dict(cls, data: dict) -> "Issue":
		return cls(
			title=data["title"],
			body=data["body"],
		)

	def __str__(self):
		return f"""Issue Title: {self.title}\n\nIssue Body: {self.body}"""
