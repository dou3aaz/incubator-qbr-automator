import pandas as pd


TEMPLATES = {
    "Feedback Emails (Post-QBR)": (
        "Cher Startup {startup_name},\n\n"
        "Suite à la revue trimestrielle (QBR) de {startup_name} qui s'est déroulée le {slot},"
        " le jury a formulé les retours suivants :\n\n"
        "[Insérer les points clés et recommandations du jury ici]\n\n"
        "Restant à votre disposition pour tout échange complémentaire.\n\n"
        "Cordialement,\n{user_signature}"
    ),
    "Reminder emails for template": (
        "Cher Startup {startup_name},\n\n"
        "Nous vous rappelons que le template de présentation et le rapport d'activité pour "
        "{startup_name} sont attendus pour la session QBR prévue le {slot}.\n\n"
        "Merci de bien vouloir nous le transmettre dans les plus brefs délais afin de préparer les jurys.\n\n"
        "Cordialement,\n{user_signature}"
    ),
    "thank you emails": (
        "Cher Startup {startup_name},\n\n"
        "Un grand merci pour votre participation active lors de la QBR de {startup_name}. "
        "Les échanges ont été très constructifs et nous saluons l'avancée de vos projets.\n\n"
        "À très bientôt,\n{user_signature}"
    ),
}


def render_template(
    template_key: str, startup_row: pd.Series, user_name: str
) -> str:
    """Renders the selected message template using live startup data and user input."""
    raw_template = TEMPLATES.get(template_key, "")

    startup_name = str(startup_row.get("Startup_Name", "la startup")).strip()
    slot = str(startup_row.get("Assigned_Slot", "Prochainement")).strip()
    if not slot:
        slot = "à planifier"

    # Format user signature generically for portfolio privacy
    clean_user = user_name.strip()
    if clean_user:
        user_signature = f"{clean_user}"
    else:
        user_signature = "Équipe d'Incubation"

    formatted_msg = raw_template.format(
        startup_name=startup_name,
        slot=slot,
        user_signature=user_signature,
    )
    return formatted_msg