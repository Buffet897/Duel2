import Shell from "@/components/Shell";

const Terms = () => (
  <Shell>
    <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-gray-950">
      Gebruiksvoorwaarden
    </h1>
    <p className="mt-1 text-sm text-gray-500">Laatst bijgewerkt: mei 2026</p>

    <hr className="my-6 border-gray-100" />

    <Section number="1" title="Over OutfitDuel">
      <p>
        OutfitDuel is een gratis online platform waarop gebruikers twee
        outfitfoto's kunnen uploaden en anderen kunnen laten stemmen welke outfit
        beter is.
      </p>
      <div className="mt-3 rounded-xl bg-gray-50 border border-gray-100 p-4 text-sm leading-relaxed text-gray-700">
        <strong className="block text-gray-900 mb-1">Aanbieder</strong>
        <strong>[Jouw naam / bedrijfsnaam]</strong>
        <br />
        [Adres], [Postcode en plaats]
        <br />
        KVK-nummer: [jouw KVK-nummer]
        <br />
        E-mail:{" "}
        <a className="text-[#7F77DD] underline-offset-4 hover:underline" href="mailto:info@outfitduel.com">
          info@outfitduel.com
        </a>
        <br />
        Website: outfitduel.com
      </div>
    </Section>

    <Section number="2" title="Toepasselijkheid">
      <p>
        Door gebruik te maken van OutfitDuel — inclusief het aanmaken van een
        duel, het stemmen of het bezoeken van de website — ga je akkoord met deze
        gebruiksvoorwaarden. Als je het niet eens bent met deze voorwaarden,
        verzoeken wij je geen gebruik te maken van OutfitDuel.
      </p>
    </Section>

    <Section number="3" title="Minimumleeftijd">
      <p>
        Je moet minimaal <strong>16 jaar</strong> oud zijn om gebruik te maken
        van OutfitDuel. Ben je jonger dan 16 jaar, dan heb je toestemming nodig
        van een ouder of voogd. Door gebruik te maken van OutfitDuel bevestig je
        dat je aan deze leeftijdseis voldoet.
      </p>
    </Section>

    <Section number="4" title="Jouw verantwoordelijkheden als gebruiker">
      <SubHeading>4.1 Wat je mag uploaden</SubHeading>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          Alleen foto's waarop <strong className="text-gray-900">jijzelf</strong>{" "}
          staat
        </li>
        <li>
          Of foto's van anderen waarvoor je{" "}
          <strong className="text-gray-900">aantoonbare toestemming</strong> hebt
          van de afgebeelde persoon
        </li>
        <li>
          Foto's die je zelf hebt gemaakt, of stockfoto's die je rechtsgeldig mag
          gebruiken
        </li>
      </ul>

      <SubHeading className="mt-5">4.2 Wat je NIET mag uploaden of doen</SubHeading>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>Foto's van anderen zonder hun toestemming (portretrecht)</li>
        <li>Seksueel expliciete, gewelddadige of aanstootgevende inhoud</li>
        <li>Inhoud die bedoeld is om andere personen te pesten, vernederen of schaden</li>
        <li>Foto's van minderjarigen in welke context dan ook</li>
        <li>
          Inhoud die inbreuk maakt op auteursrechten of andere intellectuele
          eigendomsrechten van derden
        </li>
        <li>
          Geautomatiseerde verzoeken (bots, scrapers) zonder onze uitdrukkelijke
          toestemming
        </li>
        <li>Meerdere stemmen plaatsen op hetzelfde duel via technische middelen</li>
      </ul>
    </Section>

    <Section number="5" title="Licentie op jouw content">
      <p>
        Door foto's en tekst te uploaden op OutfitDuel verleen je OutfitDuel een{" "}
        <strong className="text-gray-900">
          niet-exclusieve, royaltyvrije, wereldwijde licentie
        </strong>{" "}
        om deze inhoud te gebruiken voor het tonen van het duel op het platform.
        Deze licentie eindigt automatisch wanneer jouw duel wordt verwijderd.
      </p>
      <p className="mt-3">
        Je behoudt altijd de eigendomsrechten op jouw eigen foto's.
      </p>
    </Section>

    <Section number="6" title="Onze rechten">
      <p>OutfitDuel behoudt zich het recht voor om:</p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>
          Duels en foto's te verwijderen die in strijd zijn met deze voorwaarden,
          zonder voorafgaande kennisgeving
        </li>
        <li>
          Toegang tot het platform te blokkeren voor gebruikers die de voorwaarden
          overtreden
        </li>
        <li>De dienst tijdelijk of permanent te beëindigen</li>
        <li>Deze gebruiksvoorwaarden te wijzigen</li>
      </ul>
    </Section>

    <Section number="7" title="Aansprakelijkheid">
      <SubHeading>7.1 Inhoud van gebruikers</SubHeading>
      <p className="mt-2">
        OutfitDuel is een platform voor door gebruikers gegenereerde inhoud. Wij
        controleren inhoud niet vooraf. Wij zijn niet aansprakelijk voor de
        inhoud die gebruikers uploaden.
      </p>

      <SubHeading className="mt-5">7.2 Beperking aansprakelijkheid</SubHeading>
      <p className="mt-2">OutfitDuel is niet aansprakelijk voor:</p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>Schade als gevolg van onrechtmatige inhoud geplaatst door derden</li>
        <li>Tijdelijke onbeschikbaarheid van het platform</li>
        <li>Verlies van gegevens als gevolg van technische storingen</li>
        <li>
          Schade die voortvloeit uit het gebruik of het niet kunnen gebruiken van
          het platform
        </li>
      </ul>

      <SubHeading className="mt-5">7.3 Notice and takedown</SubHeading>
      <div className="mt-2 rounded-xl bg-[#F2F1FA] border border-[#7F77DD]/20 p-4 text-sm leading-relaxed text-[#4A45A0]">
        Meen je dat er inhoud op OutfitDuel staat die inbreuk maakt op jouw
        rechten of die anderszins onrechtmatig is? Neem dan contact op via{" "}
        <a className="underline-offset-4 hover:underline" href="mailto:abuse@outfitduel.com">
          abuse@outfitduel.com
        </a>
        . Wij behandelen meldingen binnen <strong>24 uur</strong> op werkdagen.
      </div>
    </Section>

    <Section number="8" title="Rapporteerbeleid">
      <p>Elk duel heeft een rapporteerknop. Je kunt een duel rapporteren als:</p>
      <ul className="mt-2 space-y-1.5 list-disc list-outside pl-5">
        <li>De inhoud ongepast, gewelddadig of aanstootgevend is</li>
        <li>Jij of iemand anders zonder toestemming op de foto staat</li>
        <li>Het een spamming- of frauduleuze post betreft</li>
      </ul>
      <p className="mt-3">
        Na <strong>3 rapportages</strong> wordt een duel automatisch verborgen en
        handmatig beoordeeld door OutfitDuel. Wij streven ernaar binnen{" "}
        <strong>24 uur</strong> te reageren op rapportages.
      </p>
    </Section>

    <Section number="9" title="Intellectueel eigendom">
      <p>
        Alle rechten op het platform OutfitDuel — inclusief de naam, het logo,
        het ontwerp en de software — berusten bij OutfitDuel. Het is niet
        toegestaan deze te kopiëren, te reproduceren of te gebruiken zonder
        schriftelijke toestemming.
      </p>
    </Section>

    <Section number="10" title="Toepasselijk recht">
      <p>
        Op deze gebruiksvoorwaarden is{" "}
        <strong className="text-gray-900">Nederlands recht</strong> van
        toepassing. Geschillen worden voorgelegd aan de bevoegde rechter in
        Nederland.
      </p>
    </Section>

    <Section number="11" title="Wijzigingen">
      <p>
        Wij kunnen deze gebruiksvoorwaarden aanpassen. Bij ingrijpende wijzigingen
        plaatsen wij een melding op outfitduel.com. Voortgezet gebruik na de
        datum van wijziging geldt als instemming met de nieuwe voorwaarden.
      </p>
    </Section>

    <Section number="12" title="Contact">
      <p>
        Vragen over deze gebruiksvoorwaarden? Stuur een e-mail naar{" "}
        <a className="text-[#7F77DD] underline-offset-4 hover:underline" href="mailto:info@outfitduel.com">
          info@outfitduel.com
        </a>
        .
      </p>
    </Section>

    <p className="mt-10 text-center text-xs text-gray-400 italic">
      OutfitDuel — outfitduel.com
    </p>
  </Shell>
);

const Section = ({ number, title, children }) => (
  <section className="mt-7" data-testid={`terms-section-${number}`}>
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

export default Terms;
