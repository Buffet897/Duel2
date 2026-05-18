import Shell from "@/components/Shell";

const Privacy = () => (
  <Shell>
    <h1 className="text-2xl font-bold tracking-tight text-gray-950">Privacybeleid</h1>
    <p className="mt-1 text-sm text-gray-500">Laatst bijgewerkt: {new Date().toLocaleDateString("nl-NL")}</p>

    <div className="mt-6 space-y-5 text-sm text-gray-700 leading-relaxed">
      <Block title="Welke gegevens slaan we op?">
        Voor elk duel bewaren we de geüploade foto's, een geanonimiseerde hash
        van je IP-adres (om dubbel stemmen te voorkomen) en — indien je dit zelf
        invult — je e-mailadres om je het eindresultaat te sturen. Stemmen
        worden anoniem geteld zonder profielen te bouwen.
      </Block>
      <Block title="Hoe lang bewaren we data?">
        Duels verlopen automatisch na 48 uur. Foto's worden uiterlijk 7 dagen na
        het verlopen verwijderd van onze servers. Stemtellingen blijven anoniem
        beschikbaar voor het resultaat-kaartje. E-mailadressen worden direct na
        verzenden van het eindresultaat verwijderd.
      </Block>
      <Block title="Wie kan mijn duel zien?">
        Alleen wie jij de link stuurt. Duels zijn standaard niet vindbaar via
        zoekmachines tenzij ze in onze "populair op het platform"-feed
        verschijnen. Wil je je duel verwijderen? Gebruik de Verwijder-knop op de
        resultatenpagina (zichtbaar voor de maker) of stuur ons een mail.
      </Block>
      <Block title="Contact & verwijderverzoeken">
        Mail ons via{" "}
        <a className="text-[#7F77DD] underline-offset-4 hover:underline" href="mailto:privacy@outfitduel.com">
          privacy@outfitduel.com
        </a>
        . We reageren binnen 7 dagen.
      </Block>
      <Block title="Cookies">
        We plaatsen één technische cookie (<code>od_voter</code>) om dubbel
        stemmen te helpen voorkomen. Geen tracking, geen advertentie-cookies.
      </Block>
    </div>
  </Shell>
);

const Block = ({ title, children }) => (
  <section>
    <h2 className="text-base font-display font-semibold text-gray-900">{title}</h2>
    <p className="mt-1">{children}</p>
  </section>
);

export default Privacy;
