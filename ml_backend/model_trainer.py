import random
import time
from pathlib import Path
from typing import Any

import spacy
from spacy.training import Example
from spacy.util import minibatch, compounding

from .logger import get_training_logger

logger = get_training_logger()


def parse_label_studio_annotations(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Parse Label Studio export JSON into training examples.
    Each task must contain 'data' with 'text' key and 'annotations' list.
    """
    examples = []
    for task in tasks:
        text = task.get("data", {}).get("text", "")
        if not text:
            continue
        entities = []
        for annotation in task.get("annotations", []):
            for result in annotation.get("result", []):
                if result.get("type") != "labels":
                    continue
                value = result.get("value", {})
                start = value.get("start")
                end = value.get("end")
                labels = value.get("labels", [])
                if start is None or end is None or not labels:
                    continue
                entities.append((int(start), int(end), labels[0]))
        if entities:
            examples.append({"text": text, "entities": entities})
    return examples


def _filter_overlapping_entities(entities: list[tuple[int, int, str]]) -> list[tuple[int, int, str]]:
    sorted_ents = sorted(entities, key=lambda e: (e[0], -(e[1] - e[0])))
    filtered = []
    last_end = -1
    for start, end, label in sorted_ents:
        if start >= last_end:
            filtered.append((start, end, label))
            last_end = end
    return filtered


def train_spacy_model(
    nlp: spacy.Language,
    training_data: list[dict[str, Any]],
    output_dir: Path,
    n_iter: int = 30,
    drop: float = 0.3,
    batch_size_start: float = 4.0,
    batch_size_end: float = 32.0,
    checkpoint_every: int = 10,
) -> dict[str, Any]:
    """
    Fine-tune a spaCy NER model on provided training_data.
    training_data: list of {'text': str, 'entities': [(start, end, label), ...]}
    Returns dict with training metrics and best checkpoint path.
    """
    logger.info("Starting fine-tuning: %d examples, %d iterations", len(training_data), n_iter)

    if "ner" not in nlp.pipe_names:
        ner = nlp.add_pipe("ner", last=True)
        logger.info("Added NER pipe to pipeline")
    else:
        ner = nlp.get_pipe("ner")

    for example in training_data:
        for _, _, label in example["entities"]:
            ner.add_label(label)

    other_pipes = [pipe for pipe in nlp.pipe_names if pipe != "ner"]

    spacy_examples = []
    for item in training_data:
        text = item["text"]
        entities = _filter_overlapping_entities(item["entities"])
        doc = nlp.make_doc(text)
        try:
            example_obj = Example.from_dict(doc, {"entities": entities})
            spacy_examples.append(example_obj)
        except Exception as exc:
            logger.warning("Skipping example due to error: %s | text: %.80s", exc, text)

    if not spacy_examples:
        logger.error("No valid training examples after filtering")
        return {"error": "No valid training examples", "losses": []}

    output_dir.mkdir(parents=True, exist_ok=True)
    best_loss = float("inf")
    best_checkpoint = None
    losses_history = []

    optimizer = nlp.initialize()

    start_time = time.time()
    with nlp.select_pipes(disable=other_pipes):
        for iteration in range(1, n_iter + 1):
            random.shuffle(spacy_examples)
            losses: dict[str, float] = {}
            batches = minibatch(spacy_examples, size=compounding(batch_size_start, batch_size_end, 1.001))
            for batch in batches:
                nlp.update(batch, drop=drop, losses=losses, sgd=optimizer)

            ner_loss = losses.get("ner", 0.0)
            losses_history.append({"iteration": iteration, "ner_loss": ner_loss})
            logger.info("Iteration %d/%d - NER loss: %.4f", iteration, n_iter, ner_loss)

            if ner_loss < best_loss:
                best_loss = ner_loss
                checkpoint_path = output_dir / f"checkpoint_iter_{iteration:03d}"
                nlp.to_disk(checkpoint_path)
                best_checkpoint = str(checkpoint_path)
                logger.info("New best checkpoint saved: %s (loss=%.4f)", best_checkpoint, best_loss)

            if checkpoint_every > 0 and iteration % checkpoint_every == 0:
                periodic_path = output_dir / f"checkpoint_epoch_{iteration:03d}"
                nlp.to_disk(periodic_path)
                logger.info("Periodic checkpoint saved: %s", periodic_path)

    elapsed = time.time() - start_time
    final_path = output_dir / "model_final"
    nlp.to_disk(final_path)
    logger.info("Training complete in %.1fs. Final model: %s", elapsed, final_path)

    return {
        "status": "success",
        "iterations": n_iter,
        "examples": len(spacy_examples),
        "best_loss": best_loss,
        "best_checkpoint": best_checkpoint,
        "final_model": str(final_path),
        "elapsed_seconds": round(elapsed, 2),
        "losses_history": losses_history,
    }
