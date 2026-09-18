// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { ClarificationPrompt } from "@/pages/chat/components/ClarificationPrompt";
import type { ClarificationContext, ClarificationQuestion } from "@/types/api";

afterEach(() => cleanup());

const mockQuestion: ClarificationQuestion = {
  question: "请问您期望采用哪种后端技术架构？",
  options: [
    "(推荐) FastAPI + 异步架构：轻量高性能，与现代 AI Agent 原生集成最佳",
    "Django REST framework：内置完善的 ORM 与身份认证",
    "Spring Boot / Go 微服务：高并发企业级服务体系",
    "其他（自定义输入 / 补充说明）",
  ],
  allow_custom_input: true,
  field_name: "target_framework",
};

const mockContext: ClarificationContext = {
  collected_info: {},
  asked_questions: [],
  clarification_round: 0,
  max_rounds: 3,
  intent: "dynamic_target_framework",
  original_query: "帮我规划微服务系统",
};

describe("ClarificationPrompt Component", () => {
  it("renders question text, options and round indicator", () => {
    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={mockContext}
        onAnswer={vi.fn()}
        onSkip={vi.fn()}
      />
    );

    expect(screen.getByText("请问您期望采用哪种后端技术架构？")).toBeInTheDocument();
    expect(
      screen.getByText(/FastAPI \+ 异步架构/i)
    ).toBeInTheDocument();
    expect(
      screen.getByText("其他（自定义输入 / 补充说明）")
    ).toBeInTheDocument();
  });

  it("selects recommended option and calls onAnswer on submit", () => {
    const handleAnswer = vi.fn();
    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={mockContext}
        onAnswer={handleAnswer}
        onSkip={vi.fn()}
      />
    );

    // Submit button should be disabled initially when nothing is selected
    const submitBtn = screen.getByRole("button", {
      name: /clarification\.submit|confirm|确定|确认|提交/i,
    });
    expect(submitBtn).toBeDisabled();

    // Click recommended option (first option)
    const recommendedOption = screen.getByText(/FastAPI \+ 异步架构/i);
    fireEvent.click(recommendedOption);

    // Now submit button should be enabled
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    expect(handleAnswer).toHaveBeenCalledTimes(1);
    expect(handleAnswer).toHaveBeenCalledWith(
      "target_framework",
      mockQuestion.options[0]
    );
  });

  it("expands custom input when '其他' option is clicked and submits custom text", () => {
    const handleAnswer = vi.fn();
    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={mockContext}
        onAnswer={handleAnswer}
        onSkip={vi.fn()}
      />
    );

    // Click '其他' option
    const otherOption = screen.getByText("其他（自定义输入 / 补充说明）");
    fireEvent.click(otherOption);

    // Input field should now be rendered
    const input = screen.getByPlaceholderText(/specify|请输入|补充说明/i);
    expect(input).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", {
      name: /clarification\.submit|confirm|确定|确认|提交/i,
    });
    // Still disabled because input text is empty
    expect(submitBtn).toBeDisabled();

    // Type custom input
    fireEvent.change(input, { target: { value: "自研 Rust 微服务引擎" } });
    expect(submitBtn).not.toBeDisabled();

    // Submit
    fireEvent.click(submitBtn);
    expect(handleAnswer).toHaveBeenCalledTimes(1);
    expect(handleAnswer).toHaveBeenCalledWith(
      "target_framework",
      "自研 Rust 微服务引擎"
    );
  });

  it("calls onSkip when skip button is clicked", () => {
    const handleSkip = vi.fn();
    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={mockContext}
        onAnswer={vi.fn()}
        onSkip={handleSkip}
      />
    );

    const skipBtn = screen.getByRole("button", {
      name: /clarification\.skip|skip|跳过/i,
    });
    fireEvent.click(skipBtn);

    expect(handleSkip).toHaveBeenCalledTimes(1);
  });

  it("disables buttons when isSubmitting is true", () => {
    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={mockContext}
        onAnswer={vi.fn()}
        onSkip={vi.fn()}
        isSubmitting={true}
      />
    );

    const skipBtn = screen.getByRole("button", { name: /skip|跳过/i });
    expect(skipBtn).toBeDisabled();
  });

  it("renders confirmed constraints when collected_info has entries", () => {
    const contextWithInfo: ClarificationContext = {
      ...mockContext,
      collected_info: {
        architecture: "微服务架构",
        database: "PostgreSQL",
      },
      clarification_round: 2,
    };

    render(
      <ClarificationPrompt
        question={mockQuestion}
        context={contextWithInfo}
        onAnswer={vi.fn()}
        onSkip={vi.fn()}
      />
    );

    // CollapsibleSection renders confirmed constraints
    expect(screen.getByText(/微服务架构/)).toBeInTheDocument();
    expect(screen.getByText(/PostgreSQL/)).toBeInTheDocument();
  });
});
