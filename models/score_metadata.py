from dataclasses import dataclass


@dataclass
class ScoreMetadata:
    title: str = "Untitled"
    subtitle: str = ""
    composer: str = ""
    arranger: str = ""
    copyright: str = ""

    def normalized(self):
        title = self.title.strip() or "Untitled"

        return ScoreMetadata(
            title=title,
            subtitle=self.subtitle.strip(),
            composer=self.composer.strip(),
            arranger=self.arranger.strip(),
            copyright=self.copyright.strip(),
        )
