import { useTranslation } from "react-i18next";

/**
 * Reader-facing names for the two things an answer's metadata reports by id:
 * the shape it was written in (the pipeline skill) and the tools it ran.
 *
 * Both are switches of literal `t()` keys for the reason `useAgentModeLabels`
 * gives: `i18n/locales.test.ts` only sees literal calls, and an interpolated key
 * missing from one locale renders the fallback forever with nothing reporting
 * it. An id this table does not know falls back to the id itself, which is
 * still true, just not friendly.
 *
 * `ANSWER_SHAPES` is checked against the backend's `VALID_SKILLS` by
 * `tests/agents/test_answer_shape_labels.py`, so a skill added to the router
 * without a name here fails the suite rather than showing an identifier.
 */

export const ANSWER_SHAPES = [
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
] as const;

export function useAnswerShapeLabel() {
  const { t } = useTranslation();
  return (skill: string): string => {
    switch (skill) {
      case "answer_with_citations":
        return t("answerShapes.answerWithCitations");
      case "compare_entities":
        return t("answerShapes.compareEntities");
      case "timeline_builder":
        return t("answerShapes.timelineBuilder");
      case "web_fact_check":
        return t("answerShapes.webFactCheck");
      case "cyber_attack_analysis":
        return t("answerShapes.cyberAttackAnalysis");
      case "cyber_defense_hardening":
        return t("answerShapes.cyberDefenseHardening");
      case "incident_response_playbook":
        return t("answerShapes.incidentResponsePlaybook");
      case "vulnerability_exposure_assessment":
        return t("answerShapes.vulnerabilityExposureAssessment");
      case "ai_knowledge_assistant":
        return t("answerShapes.aiKnowledgeAssistant");
      case "ai_engineering_estimate":
        return t("answerShapes.aiEngineeringEstimate");
      case "pdf_text_reader":
        return t("answerShapes.pdfTextReader");
      case "data_analysis_report":
        return t("answerShapes.dataAnalysisReport");
      case "compliance_gap_analysis":
        return t("answerShapes.complianceGapAnalysis");
      default:
        return skill;
    }
  };
}

export function useToolLabel() {
  const { t } = useTranslation();
  return (toolId: string): string => {
    switch (toolId) {
      case "querymind_cyber_cve_lookup":
        return t("toolNames.cveLookup");
      case "querymind_cyber_mitre_attack":
        return t("toolNames.mitreAttack");
      case "querymind_cyber_product_exposure":
        return t("toolNames.productExposure");
      case "querymind_cyber_indicator_extract":
        return t("toolNames.indicatorExtract");
      case "querymind_ai_memory_estimate":
        return t("toolNames.memoryEstimate");
      case "querymind_ai_compute_estimate":
        return t("toolNames.computeEstimate");
      case "querymind_ai_math_eval":
        return t("toolNames.mathEval");
      case "querymind_ai_specification_extract":
        return t("toolNames.specificationExtract");
      case "querymind_table_list":
        return t("toolNames.tableList");
      case "querymind_table_query":
        return t("toolNames.tableQuery");
      case "querymind_compliance_citation_extract":
        return t("toolNames.complianceCitationExtract");
      case "querymind_document_locations":
        return t("toolNames.documentLocations");
      case "querymind_connector_list_owned":
        return t("toolNames.connectorListOwned");
      case "querymind_connector_disable_owned":
        return t("toolNames.connectorDisableOwned");
      case "querymind_tool_selector":
        return t("toolNames.toolSelector");
      default:
        return toolId;
    }
  };
}
