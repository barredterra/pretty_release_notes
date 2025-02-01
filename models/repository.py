from dataclasses import dataclass


@dataclass
class Repository:
	owner: str
	name: str

	@property
	def url(self):
		return f"https://github.com/{self.owner}/{self.name}"
