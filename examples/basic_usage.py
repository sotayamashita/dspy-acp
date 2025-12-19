"""Basic usage example for dspy-acp."""

import dspy

from dspy_acp import CodexACPAdapter

# Initialize the ACP adapter for Codex via ACP
lm = CodexACPAdapter()
dspy.configure(lm=lm)


# Define a Q&A signature
class QA(dspy.Signature):
    """Answer the user's question concisely and accurately."""

    question = dspy.InputField()
    answer = dspy.OutputField(desc="100 characters or less")


# Create a Chain of Thought module
qa_system = dspy.ChainOfThought(QA)

if __name__ == "__main__":
    question = "What is the main benefit of using DSPy with ACP?"

    print("Sending prompt to ACP agent...")
    try:
        response = qa_system(question=question)

        print("-" * 50)
        print(f"Question: {question}")
        if hasattr(response, "reasoning") and response.reasoning:
            print(f"Reasoning: {response.reasoning}")
        print(f"Answer: {response.answer}")
        print("-" * 50)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        lm.close()
