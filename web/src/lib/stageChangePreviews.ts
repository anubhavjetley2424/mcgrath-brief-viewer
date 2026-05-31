/**
 * User-facing confirmation text shown when Simon drags a deal
 * to a new stage on the Kanban board.
 *
 * Key = target stage name. Value = markdown-ish plain text
 * describing what automation will fire.
 */
export const STAGE_CHANGE_PREVIEWS: Record<string, string> = {
  'Listing Appointment Booked':
    'This will send the vendor a confirmation email + SMS, create a calendar event, and schedule a 24-hour appointment reminder SMS.',

  'Pre-Appointment Prep':
    'This will create 5 prep tasks for you (RP Data, Pricefinder CMA, marketing quote, listing slides, 24h confirmation reminder). No vendor communication.',

  'Appraisal Completed':
    'This will draft a follow-up email for you to review and approve before sending, plus schedule a 3-day check-in reminder SMS to you.',

  'Negotiation':
    'This will create 3 follow-up tasks (day 2, 5, 10) and schedule matching SMS nudges to remind you. No vendor communication is sent automatically.',

  'Listing Signed':
    'This will draft a welcome email (you approve before sending) and create 6 campaign kickoff tasks (photography, B&P, Agentbox, signboard, WhatsApp group).',

  'Campaign Live':
    'This will draft a "listing is live" email for your approval, create a recurring weekly vendor update task, and schedule weekly SMS reminders to you.',

  'Sold':
    'This will draft a congratulations email (you approve before sending), create a task to call the vendor personally, and schedule 6-month and 12-month follow-up SMS to the vendor.',
};

/**
 * Returns preview text for a stage change, or null if no preview needed
 * (e.g. moving to "New Lead" has no automation).
 */
export function getStageChangePreview(targetStage: string): string | null {
  return STAGE_CHANGE_PREVIEWS[targetStage] ?? null;
}
