from html import escape

from models.score_metadata import ScoreMetadata
from notation.rhythm_quantizer import RhythmQuantizer
from notation.tonality import AUTOMATIC_TONALITY, key_signature_fifths


class MusicXMLExporter:
    DIVISIONS = 8  # quarter note = 8 units
    PAGE_WIDTH = 1194
    PAGE_HEIGHT = 1545
    PAGE_CENTER_X = PAGE_WIDTH // 2
    PAGE_RIGHT_X = PAGE_WIDTH - 70
    TITLE_Y = PAGE_HEIGHT - 80
    SUBTITLE_Y = PAGE_HEIGHT - 130
    COMPOSER_Y = PAGE_HEIGHT - 210
    COPYRIGHT_Y = 45

    def export(
        self,
        notes,
        output_path: str,
        bpm: int = 60,
        time_signature: str = "4/4",
        use_tempo_quantization: bool = True,
        tonality: str = AUTOMATIC_TONALITY,
        score_metadata: ScoreMetadata | None = None,
    ):
        score_metadata = (score_metadata or ScoreMetadata()).normalized()

        if use_tempo_quantization:
            measures_xml = self.build_piano_measures(
                RhythmQuantizer(
                    bpm=bpm,
                    time_signature=time_signature,
                ).quantize(notes),
                tonality=tonality,
            )
        else:
            measures_xml = self.build_legacy_piano_measures(
                notes,
                tonality=tonality,
            )

        content = f"""<?xml version="1.0" encoding="UTF-8" standalone="no"?>
<!DOCTYPE score-partwise PUBLIC
    "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
    "http://www.musicxml.org/dtds/partwise.dtd">

<score-partwise version="3.1">
  {self.build_score_metadata_xml(score_metadata)}

  <part-list>

    <score-part id="P1">
        <part-name>Piano</part-name>
        <score-instrument id="P1-I1">
            <instrument-name>Piano</instrument-name>
        </score-instrument>
        <midi-instrument id="P1-I1">
            <midi-channel>1</midi-channel>
            <midi-program>1</midi-program>
        </midi-instrument>
    </score-part>
  </part-list>

  <part id="P1">
{measures_xml}
  </part>
</score-partwise>
"""
        with open(output_path, "w", encoding="utf-8") as file:
            file.write(content)

    def build_score_metadata_xml(self, score_metadata: ScoreMetadata):
        title = self.xml_text(score_metadata.title)
        subtitle = self.xml_text(score_metadata.subtitle)
        composer = self.xml_text(score_metadata.composer)
        arranger = self.xml_text(score_metadata.arranger)
        copyright_text = self.xml_text(score_metadata.copyright)

        creators = ""

        if composer:
            creators += f"""
    <creator type="composer">{composer}</creator>"""

        if arranger:
            creators += f"""
    <creator type="arranger">{arranger}</creator>"""

        rights = ""

        if copyright_text:
            rights = f"""
    <rights>{copyright_text}</rights>"""

        identification = ""

        if creators or rights:
            identification = f"""
  <identification>{creators}{rights}
  </identification>"""

        subtitle_credit = ""

        if subtitle:
            subtitle_credit = f"""
  <credit page="1">
    <credit-words default-x="{self.PAGE_CENTER_X}" default-y="{self.SUBTITLE_Y}" justify="center" valign="top" font-size="14">&#10;&#10;{subtitle}</credit-words>
  </credit>"""

        author_lines = []

        if composer:
            author_lines.append(f"Composer: {composer}")

        if arranger:
            author_lines.append(f"Arranger: {arranger}")

        author_credit = ""

        if author_lines:
            author_credit = f"""
  <credit page="1">
    <credit-words default-x="{self.PAGE_RIGHT_X}" default-y="{self.COMPOSER_Y}" justify="right" valign="top" font-size="11">{"&#10;".join(author_lines)}</credit-words>
  </credit>"""

        copyright_credit = ""

        if copyright_text:
            copyright_credit = f"""
  <credit page="1">
    <credit-words default-x="{self.PAGE_CENTER_X}" default-y="{self.COPYRIGHT_Y}" justify="center" valign="bottom" font-size="8">{copyright_text}</credit-words>
  </credit>"""

        return f"""<movement-title>{title}</movement-title>{identification}
  <defaults>
    <scaling>
      <millimeters>7</millimeters>
      <tenths>40</tenths>
    </scaling>
    <page-layout>
      <page-height>{self.PAGE_HEIGHT}</page-height>
      <page-width>{self.PAGE_WIDTH}</page-width>
      <page-margins type="both">
        <left-margin>70</left-margin>
        <right-margin>70</right-margin>
        <top-margin>70</top-margin>
        <bottom-margin>70</bottom-margin>
      </page-margins>
    </page-layout>
  </defaults>
  <credit page="1">
    <credit-words default-x="{self.PAGE_CENTER_X}" default-y="{self.TITLE_Y}" justify="center" valign="top" font-size="26" font-weight="bold">{title}</credit-words>
  </credit>{subtitle_credit}{author_credit}{copyright_credit}"""

    def xml_text(self, value):
        return escape(str(value or ""), quote=True)

    def build_first_system_layout_xml(self):
        return """
        <print>
          <system-layout>
            <top-system-distance>240</top-system-distance>
          </system-layout>
        </print>
    """

    def build_legacy_piano_measures(self, notes, tonality=AUTOMATIC_TONALITY):
        if not notes:
            return self.empty_measure(1, tonality=tonality)

        events = []
        previous_end = 0.0

        for note in notes:
            gap = note.start_time - previous_end

            if gap > 0.15:
                rest_units = self.duration_to_units(gap)
                events.append(("rest", rest_units))

            if note.is_rest():
                events.append(("rest", self.duration_to_units(note.duration)))
            else:
                events.append(("note", note))

            previous_end = note.start_time + note.duration

        measure_duration = self.DIVISIONS * 4
        current_measure = []
        current_duration = 0
        measure_number = 1
        xml = ""

        for event_type, value in events:
            if event_type == "note":
                duration_units = self.duration_to_units(value.duration)
            else:
                duration_units = value

            if current_duration + duration_units > measure_duration:
                xml += self.build_legacy_measure(
                    measure_number,
                    current_measure,
                    include_attributes=(measure_number == 1),
                    tonality=tonality,
                )
                measure_number += 1
                current_measure = []
                current_duration = 0

            current_measure.append((event_type, value))
            current_duration += duration_units

        if current_measure:
            xml += self.build_legacy_measure(
                measure_number,
                current_measure,
                include_attributes=(measure_number == 1),
                tonality=tonality,
            )

        return xml

    def build_legacy_measure(
        self,
        measure_number,
        events,
        include_attributes=False,
        tonality=AUTOMATIC_TONALITY,
    ):
        attributes = ""
        system_break = ""

        if measure_number > 1 and (measure_number - 1) % 4 == 0:
            system_break = """
        <print new-system="yes"/>
    """
        elif include_attributes:
            system_break = self.build_first_system_layout_xml()

        if include_attributes:
            fifths = key_signature_fifths(tonality)
            attributes = f"""
        <attributes>
            <divisions>{self.DIVISIONS}</divisions>
            <key>
            <fifths>{fifths}</fifths>
            </key>
            <time>
            <beats>4</beats>
            <beat-type>4</beat-type>
            </time>
            <staves>2</staves>
            <clef number="1">
            <sign>G</sign>
            <line>2</line>
            </clef>
            <clef number="2">
            <sign>F</sign>
            <line>4</line>
            </clef>
        </attributes>
    """

        xml = ""

        for event_type, value in events:
            if event_type == "note":
                if self.is_chord(value):
                    xml += self.build_chord_xml(value)
                else:
                    xml += self.build_note_xml(value)

            elif event_type == "rest":
                xml += self.build_rest_xml(value)

        return f"""
        <measure number="{measure_number}">
    {system_break}
    {attributes}
    {xml}
        </measure>
    """

    def build_piano_measures(self, quantized_score, tonality=AUTOMATIC_TONALITY):
        if not quantized_score.measures:
            return self.empty_measure(1, tonality=tonality)

        xml = ""

        for measure in quantized_score.measures:
            xml += self.build_measure(
                measure.number,
                measure.events,
                quantized_score,
                include_attributes=(measure.number == 1),
                tonality=tonality,
            )

        return xml

    def build_measure(
        self,
        measure_number,
        events,
        quantized_score,
        include_attributes=False,
        tonality=AUTOMATIC_TONALITY,
    ):
        attributes = ""
        system_break = ""
        direction = ""

        if measure_number > 1 and (measure_number - 1) % 4 == 0:
            system_break = """
        <print new-system="yes"/>
    """
        elif include_attributes:
            system_break = self.build_first_system_layout_xml()

        if include_attributes:
            time_signature = quantized_score.time_signature
            fifths = key_signature_fifths(tonality)
            attributes = f"""
        <attributes>
            <divisions>{quantized_score.divisions}</divisions>
            <key>
            <fifths>{fifths}</fifths>
            </key>
            <time>
            <beats>{time_signature.beats}</beats>
            <beat-type>{time_signature.beat_type}</beat-type>
            </time>
            <staves>2</staves>
            <clef number="1">
            <sign>G</sign>
            <line>2</line>
            </clef>
            <clef number="2">
            <sign>F</sign>
            <line>4</line>
            </clef>
        </attributes>
    """
            direction = f"""
        <direction placement="above">
          <direction-type>
            <metronome>
              <beat-unit>quarter</beat-unit>
              <per-minute>{quantized_score.bpm}</per-minute>
            </metronome>
          </direction-type>
          <sound tempo="{quantized_score.bpm}"/>
        </direction>
    """

        xml = ""

        for event in events:
            if event.kind == "note":
                if self.is_chord(event.note):
                    xml += self.build_chord_xml(
                        event.note,
                        event.duration_units,
                        tie_start=event.tie_start,
                        tie_stop=event.tie_stop,
                    )
                else:
                    xml += self.build_note_xml(
                        event.note,
                        event.duration_units,
                        tie_start=event.tie_start,
                        tie_stop=event.tie_stop,
                    )

            elif event.kind == "rest":
                xml += self.build_rest_xml(event.duration_units)

        return f"""
        <measure number="{measure_number}">
    {system_break}
    {attributes}
    {direction}
    {xml}
        </measure>
    """
        

    def build_note_xml(
        self,
        note,
        duration_units=None,
        tie_start=False,
        tie_stop=False,
    ):
        if note.is_rest():
            if duration_units is None:
                duration_units = self.duration_to_units(note.duration)

            return self.build_rest_xml(duration_units)

        note_name = self.clean_note_name(note.name)
        step = note_name[0]
        octave = self.get_octave(note_name)
        alter = self.get_alter(note_name)

        if duration_units is None:
            duration_units = self.duration_to_units(note.duration)

        note_type = self.duration_to_type(duration_units)
        dot_xml = self.build_dot_xml(duration_units)
        tie_xml = self.build_tie_xml(tie_start, tie_stop)
        notations_xml = self.build_notations_xml(tie_start, tie_stop)

        staff = self.staff_number(note, octave)

        alter_xml = ""
        if alter != 0:
            alter_xml = f"<alter>{alter}</alter>"

        return f"""
      <note>
        <pitch>
          <step>{step}</step>
          {alter_xml}
          <octave>{octave}</octave>
        </pitch>
        <duration>{duration_units}</duration>
        {tie_xml}
        <type>{note_type}</type>
        {dot_xml}
        <staff>{staff}</staff>
        {notations_xml}
      </note>
"""

    def build_rest_xml(self, duration_units):
        note_type = self.duration_to_type(duration_units)
        dot_xml = self.build_dot_xml(duration_units)

        return f"""
      <note>
        <rest/>
        <duration>{duration_units}</duration>
        <type>{note_type}</type>
        {dot_xml}
      </note>
"""

    def empty_measure(self, measure_number, tonality=AUTOMATIC_TONALITY):
        fifths = key_signature_fifths(tonality)
        return f"""
    <measure number="{measure_number}">
      <attributes>
        <divisions>{self.DIVISIONS}</divisions>
        <key>
          <fifths>{fifths}</fifths>
        </key>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <staves>2</staves>
        <clef number="1">
          <sign>G</sign>
          <line>2</line>
        </clef>
        <clef number="2">
          <sign>F</sign>
          <line>4</line>
        </clef>
      </attributes>
      {self.build_rest_xml(self.DIVISIONS * 4)}
    </measure>
"""

    def duration_to_units(self, duration_seconds):
        if duration_seconds < 0.35:
            return 4
        elif duration_seconds < 0.75:
            return 8
        elif duration_seconds < 1.5:
            return 16
        else:
            return 32

    def duration_to_type(self, duration_units):
        if duration_units == 1:
            return "32nd"
        elif duration_units in (2, 3):
            return "16th"
        elif duration_units in (4, 6):
            return "eighth"
        elif duration_units in (8, 12):
            return "quarter"
        elif duration_units in (16, 24):
            return "half"
        elif duration_units == 32:
            return "whole"
        return "quarter"

    def build_dot_xml(self, duration_units):
        if duration_units in (3, 6, 12, 24):
            return "<dot/>"

        return ""

    def build_tie_xml(self, tie_start, tie_stop):
        tie_xml = ""

        if tie_stop:
            tie_xml += '<tie type="stop"/>'

        if tie_start:
            tie_xml += '<tie type="start"/>'

        return tie_xml

    def build_notations_xml(self, tie_start, tie_stop):
        tied_xml = ""

        if tie_stop:
            tied_xml += '<tied type="stop"/>'

        if tie_start:
            tied_xml += '<tied type="start"/>'

        if not tied_xml:
            return ""

        return f"<notations>{tied_xml}</notations>"

    def clean_note_name(self, note_name):
        return note_name.replace("♯", "#").replace("♭", "b")

    def get_octave(self, note_name):
        for char in reversed(note_name):
            if char.isdigit():
                return int(char)
        return 4

    def get_alter(self, note_name):
        if "#" in note_name:
            return 1
        if "b" in note_name:
            return -1
        return 0

    def is_chord(self, event):
        return hasattr(event, "names")

    def build_chord_xml(
        self,
        chord,
        duration_units=None,
        tie_start=False,
        tie_stop=False,
    ):
        xml = ""

        if duration_units is None:
            duration_units = self.duration_to_units(chord.duration)

        note_type = self.duration_to_type(duration_units)
        dot_xml = self.build_dot_xml(duration_units)
        tie_xml = self.build_tie_xml(tie_start, tie_stop)
        notations_xml = self.build_notations_xml(tie_start, tie_stop)

        for index, note_name in enumerate(chord.names):
            note_name = self.clean_note_name(note_name)

            step = note_name[0]
            octave = self.get_octave(note_name)
            alter = self.get_alter(note_name)

            staff = self.staff_number(chord, octave)

            alter_xml = ""
            if alter != 0:
                alter_xml = f"<alter>{alter}</alter>"

            chord_xml = ""
            if index > 0:
                chord_xml = "<chord/>"

            xml += f"""
          <note>
            {chord_xml}
              <pitch>
                <step>{step}</step>
                {alter_xml}
                <octave>{octave}</octave>
              </pitch>
              <duration>{duration_units}</duration>
              {tie_xml}
              <type>{note_type}</type>
              {dot_xml}
              <staff>{staff}</staff>
              {notations_xml}
            </note>
    """

        return xml

    def staff_number(self, note_or_chord, octave):
        staff_choice = getattr(note_or_chord, "staff", "auto")

        if staff_choice == "treble":
            return 1
        if staff_choice == "bass":
            return 2

        return 1 if octave >= 4 else 2
