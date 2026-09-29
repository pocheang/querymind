import { useTranslation } from "react-i18next";

/**
 * Reader-facing names for the two things an answer's metadata reports by id:
 * the shape it was written in (the pipeline skill) and the tools it ran.
 *
 * The locale key is derived from the id -- `answer_with_citations` is
 * `answerShapes.answerWithCitations`, `querymind_cyber_cve_lookup` is
 * `toolNames.cyberCveLookup` -- so there is no second table to keep in step.
 * A derived key is invisible to `i18n/locales.test.ts`, which only sees literal
 * `t("...")` calls, so `answerLabels.test.ts` does its job here: every id listed
 * below must resolve in both locales. An id not listed keeps its identifier,
 * which is still true, just not friendly.
 *
 * `ANSWER_SHAPES` is checked against the backend's `VALID_SKILLS`, and
 * `TOOL_IDS` against every tool id in `app/`, by
 * `tests/agents/test_answer_shape_labels.py`.
 */

export const ANSWER_SHAPES: readonly string[] = [
  "answer_with_citations",
  "compare_entities",
  "timeline_builder",
  "web_fact_check",
  "cyber_attack_analysis",
  "cyber_defense_hardening",
  "incident_response_playbook",
  "vulnerability_exposure_assessment",
  "ai_knowledge_assistant",
  "ai_engineering_estimate",
  "pdf_text_reader",
  "data_analysis_report",
  "compliance_gap_analysis",
];

export const TOOL_IDS: readonly string[] = [
  "querymind_cyber_cve_lookup",
  "querymind_cyber_mitre_attack",
  "querymind_cyber_product_exposure",
  "querymind_cyber_indicator_extract",
  "querymind_ai_memory_estimate",
  "querymind_ai_compute_estimate",
  "querymind_ai_math_eval",
  "querymind_ai_specification_extract",
  "querymind_table_list",
  "querymind_table_query",
  "querymind_compliance_citation_extract",
  "querymind_document_locations",
  "querymind_connector_list_owned",
  "querymind_connector_disable_owned",
  "querymind_tool_selector",
];

function camelCase(id: string): string {
  return id.replace(/_([a-z])/g, (_match, letter: string) => letter.toUpperCase());
}

export function answerShapeKey(skill: string): string {
  return `answerShapes.${camelCase(skill)}`;
}

export function toolNameKey(toolId: string): string {
  return `toolNames.${camelCase(toolId.replace(/^querymind_/, ""))}`;
}

export function useAnswerShapeLabel() {
  const { t } = useTranslation();
  return (skill: string): string => (ANSWER_SHAPES.includes(skill) ? t(answerShapeKey(skill)) : skill);
}

export function useToolLabel() {
  const { t } = useTranslation();
  return (toolId: string): string => (TOOL_IDS.includes(toolId) ? t(toolNameKey(toolId)) : toolId);
}
