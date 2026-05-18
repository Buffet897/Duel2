import Shell from "@/components/Shell";

const Privacy = () => (
  <Shell>
    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-950">
      Privacybeleid
    </h1>
    <p className="mt-1 text-sm text-gray-500">Laatst bijgewerkt: mei 2026</p>

    <hr className="my-6 border-gray-100" />

    <Section number="1" title="Wie zijn wij?">
      <p>OutfitDuel is een dienst van:</p>
      <div className="mt-2 rounded-xl bg-gray-50 border border-gray-100 p-4 text-sm leading-relaxed text-gray-700">
        <strong>[Jouw naam / bedrijfsnaam]</strong>
        <br />
        [Adres]
        <br />
        [Postcode en plaats]
        <br />
        KVK-nummer: [jouw KVK-nummer]
        <br />
        E-mail:{" "}
        <a className="text-[#7F77DD] underline-offset-4 hover:underline" href="mailto:privacy@outfitduel.com">
          privacy@outfitduel.com
        </a>
      </div>
    </Section>

    <Section number="2" title="Wat is OutfitDuel?">
      <p>
        OutfitDuel is een gratis online platform waarop gebruikers twee
        outfitfoto's kunnen uploaden en anderen kunnen laten stemmen welke outfit
        beter is. De dienst is beschikbaar via{" "}
        <span className="font-medium text-gray-900">outfitduel.com</span>.
      </p>
    </Section>

    <Section number="3" title="Welke gegevens verwerken wij?">
      <SubHeading>3.1 Gegevens die je zelf verstrekt</SubHeading>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          <strong className="text-gray-900">Foto's:</strong> de twee outfitfoto's
          die je uploadt voor een duel
        </li>
        <li>
          <strong className="text-gray-900">Jouw vraag:</strong> de tekst die je
          bij een duel invoert (optioneel, max 80 tekens)
        </li>
        <li>
          <strong className="text-gray-900">E-mailadres:</strong> alleen als je
          dit vrijwillig invult om het duelresultaat te ontvangen. Dit is volledig
          optioneel.
        </li>
      </ul>

      <SubHeading className="mt-5">3.2 Gegevens die automatisch worden verzameld</SubHeading>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          <strong className="text-gray-900">IP-adres (gehashed):</strong> we slaan
          een versleutelde versie van je IP-adres op om dubbel stemmen te
          voorkomen. We bewaren niet je volledige IP-adres.
        </li>
        <li>
          <strong className="text-gray-900">Browser-cookie:</strong> een anonieme
          sessiecode om te onthouden dat je al gestemd hebt op een duel. Dit is
          een functionele cookie — geen tracking.
        </li>
      </ul>

      <SubHeading className="mt-5">3.3 Wat wij NIET verzamelen</SubHeading>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>Wij verzamelen geen naam, geboortedatum of andere persoonsgegevens</li>
        <li>Wij plaatsen geen advertentiecookies of tracking pixels</li>
        <li>Wij delen geen gegevens met advertentienetwerken</li>
        <li>Wij verkopen geen gegevens aan derden</li>
      </ul>
    </Section>

    <Section number="4" title="Waarvoor gebruiken wij jouw gegevens?">
      <Table
        head={["Gegeven", "Doel", "Rechtsgrond"]}
        rows={[
          ["Foto's", "Tonen van het duel aan bezoekers", "Toestemming (door uploaden)"],
          ["E-mailadres", "Versturen van duelresultaat", "Toestemming (vrijwillig ingevuld)"],
          ["IP-hash + cookie", "Voorkomen van dubbel stemmen", "Gerechtvaardigd belang"],
        ]}
      />
    </Section>

    <Section number="5" title="Hoe lang bewaren wij jouw gegevens?">
      <ul className="space-y-2 list-disc list-outside pl-5">
        <li>
          <strong className="text-gray-900">Foto's:</strong> worden automatisch
          verwijderd <strong>7 dagen na het verlopen van een duel</strong> (duels
          verlopen na 48 uur). Dit betekent dat foto's maximaal 9 dagen bewaard
          worden.
        </li>
        <li>
          <strong className="text-gray-900">E-mailadres:</strong> wordt verwijderd
          zodra het duelresultaat is verstuurd, uiterlijk 7 dagen na aanmaken van
          het duel.
        </li>
        <li>
          <strong className="text-gray-900">IP-hash:</strong> wordt verwijderd 30
          dagen na de laatste stemactie.
        </li>
        <li>
          <strong className="text-gray-900">Browser-cookie:</strong> vervalt
          automatisch na 30 dagen of bij het wissen van je browsergeschiedenis.
        </li>
      </ul>
    </Section>

    <Section number="6" title="Delen wij jouw gegevens?">
      <p>Wij delen jouw gegevens niet met derden, behalve:</p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          <strong className="text-gray-900">Emergent (hostingprovider):</strong>{" "}
          onze technische hostingpartner verwerkt gegevens om de dienst te kunnen
          aanbieden. Emergent treedt op als verwerker in de zin van de AVG.
        </li>
        <li>
          <strong className="text-gray-900">Wettelijke verplichting:</strong> als
          een rechter of autoriteit ons verplicht gegevens te verstrekken, zijn
          wij daartoe gehouden.
        </li>
      </ul>
    </Section>

    <Section number="7" title="Jouw rechten">
      <p>
        Op grond van de Algemene Verordening Gegevensbescherming (AVG) heb je de
        volgende rechten:
      </p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          <strong className="text-gray-900">Inzagerecht:</strong> je kunt opvragen
          welke gegevens wij van jou bewaren
        </li>
        <li>
          <strong className="text-gray-900">Verwijderingsrecht:</strong> je kunt
          verwijdering van jouw duel en foto's aanvragen
        </li>
        <li>
          <strong className="text-gray-900">Recht op bezwaar:</strong> je kunt
          bezwaar maken tegen verwerking op basis van gerechtvaardigd belang
        </li>
        <li>
          <strong className="text-gray-900">Recht op overdraagbaarheid:</strong>{" "}
          je kunt je gegevens opvragen in een gangbaar formaat
        </li>
      </ul>
      <div className="mt-3 rounded-xl bg-[#F2F1FA] border border-[#7F77DD]/20 p-4 text-sm leading-relaxed text-[#4A45A0]">
        <strong>Verzoeken indienen:</strong> stuur een e-mail naar{" "}
        <a className="underline-offset-4 hover:underline" href="mailto:privacy@outfitduel.com">
          privacy@outfitduel.com
        </a>
        . Wij reageren binnen <strong>30 dagen</strong>.
      </div>
    </Section>

    <Section number="8" title="Minderjarigen">
      <p>
        OutfitDuel is niet bedoeld voor kinderen jonger dan 16 jaar. Gebruikers
        dienen minimaal 16 jaar oud te zijn om een duel aan te maken. Door gebruik
        te maken van OutfitDuel bevestig je dat je 16 jaar of ouder bent, of dat
        je toestemming hebt van een ouder of voogd.
      </p>
    </Section>

    <Section number="9" title="Beveiliging">
      <p>Wij nemen passende technische maatregelen om jouw gegevens te beschermen:</p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>Alle communicatie verloopt via HTTPS (versleutelde verbinding)</li>
        <li>Foto's worden opgeslagen in een beveiligde omgeving zonder directe uitvoerrechten</li>
        <li>EXIF-metadata (inclusief GPS-locatie) wordt automatisch verwijderd uit geüploade foto's</li>
        <li>IP-adressen worden direct bij opslag gehasht en zijn niet te herleiden</li>
      </ul>
    </Section>

    <Section number="10" title="Cookies">
      <p>
        OutfitDuel gebruikt uitsluitend <strong>functionele cookies</strong> —
        geen tracking of advertentiecookies.
      </p>
      <Table
        head={["Cookie", "Doel", "Bewaartermijn"]}
        rows={[
          ["od_vote_[duel_id]", "Bijhouden of je al gestemd hebt op een duel", "30 dagen"],
          ["od_session", "Anonieme sessiecookie voor anti-spam", "Sessie (sluit bij browser)"],
        ]}
        mono
      />
      <p className="mt-3">
        Voor functionele cookies is geen toestemming vereist op grond van de
        Telecommunicatiewet. Wij tonen wel een kort cookiebericht bij eerste
        bezoek.
      </p>
    </Section>

    <Section number="11" title="Klachten">
      <p>
        Ben je niet tevreden over hoe wij jouw gegevens verwerken? Je hebt het
        recht een klacht in te dienen bij de{" "}
        <strong className="text-gray-900">Autoriteit Persoonsgegevens</strong>:
      </p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          Website:{" "}
          <a
            className="text-[#7F77DD] underline-offset-4 hover:underline"
            href="https://autoriteitpersoonsgegevens.nl"
            target="_blank"
            rel="noreferrer noopener"
          >
            autoriteitpersoonsgegevens.nl
          </a>
        </li>
        <li>Telefoon: 088 - 1805 250</li>
      </ul>
    </Section>

    <Section number="12" title="Wijzigingen">
      <p>
        Wij kunnen dit privacybeleid aanpassen. Bij belangrijke wijzigingen
        plaatsen wij een melding op outfitduel.com. De datum bovenaan dit document
        geeft aan wanneer het voor het laatst is bijgewerkt.
      </p>
    </Section>

    <p className="mt-10 text-center text-xs text-gray-400 italic">
      Vragen? Stuur een e-mail naar{" "}
      <a className="text-[#7F77DD] not-italic underline-offset-4 hover:underline" href="mailto:privacy@outfitduel.com">
        privacy@outfitduel.com
      </a>
    </p>
  </Shell>
);

const Section = ({ number, title, children }) => (
  <section className="mt-7" data-testid={`privacy-section-${number}`}>
    <div className="flex items-baseline gap-3">
      <span className="text-xs font-semibold tracking-[0.05em] text-[#7F77DD]">
        {number.padStart(2, "0")}
      </span>
      <h2 className="text-lg sm:text-xl font-display font-semibold text-gray-950">
        {title}
      </h2>
    </div>
    <div className="mt-3 text-sm text-gray-700 leading-relaxed">{children}</div>
  </section>
);

const SubHeading = ({ children, className = "" }) => (
  <h3 className={`text-sm font-semibold text-gray-900 ${className}`}>{children}</h3>
);

const Table = ({ head, rows, mono = false }) => (
  <div className="mt-3 overflow-x-auto rounded-xl border border-gray-100">
    <table className="w-full text-xs sm:text-sm">
      <thead className="bg-gray-50 text-gray-500">
        <tr>
          {head.map((h) => (
            <th key={h} className="text-left font-semibold uppercase tracking-wider text-[11px] px-3 py-2.5">
              {h}
            </th>
          ))}
        </tr>
      </thead>
      <tbody className="text-gray-700">
        {rows.map((r, i) => (
          <tr key={i} className="border-t border-gray-100 align-top">
            {r.map((cell, j) => (
              <td
                key={j}
                className={`px-3 py-2.5 ${j === 0 && mono ? "font-mono text-[#4A45A0]" : ""} ${j === 0 ? "font-medium text-gray-900" : ""}`}
              >
                {cell}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

export default Privacy;
