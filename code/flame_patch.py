"""Apply verified corrections to corpus/flame_timeline.json from the 2026-09-09 verification pass."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'corpus', 'flame_timeline.json')
rows = json.load(open(P, encoding='utf-8'))
IDX = {r['id']: r for r in rows}

PATCH = {
 'bahhar2023': {
  'pub_date': '2023-01-02',
  'protocol': 'INTERNALLY_INCONSISTENT',
  'headline_accuracy': 99.3,
  'accuracy_kind': 'reported against the official 8,617-frame test set, but the same paper states a shuffled 70/20 re-split of the 39,375 pool',
  'split_sentence_verbatim': "The generated dataset from the video of 29 FPS is 39,375, including 25,018 frames for the “fire” class and 14,357 for the “no-fire” class. The data was divided into a 70% training and 20% testing portion, with additional testing conducted in two stages. All samples are shuffled before being fed into the DL model. || To evaluate the accuracy and loss of the model, the test dataset contained 8617 frames, including 5137 fire-labeled frames and 3480 non-fire-labeled frames, which were fed into the pre-trained networks.",
  'image_counts': '39,375 shuffled into 70% train / 20% test; AND separately an 8,617-frame evaluation set with the correct 5,137/3,480 class split',
  'other_reported': {'Xception': 99.0, 'MobileNetV2': 99.3, 'ResNet50': 99.0,
                     'sensitivity': 0.996, 'specificity': 0.983},
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (electronics-12-00228). Table 2 verbatim: “Metrics Xception Baseline MobileNetV2 Baseline ResNet-50 Baseline | Accuracy 0.99 0.993 0.99 | Sensitivity 0.992 0.996 0.996 | Specificity 0.981 0.981 0.983 | NPV 0.976 0.994 0.987”',
  'verification': 'RECLASSIFIED this session. Previously coded RANDOM_RESPLIT on the assumption that its 8,617 sentence was inherited boilerplate. It is not boilerplate - it sits in the experimental-setup paragraph and carries the correct class composition (5,137 fire / 3,480 no-fire). The paper therefore CLAIMS 99.0-99.3% ON THE OFFICIAL TEST SET while also stating a shuffled 70/20 split of the training pool. The two statements cannot both be true (and 70+20 does not reach 100). THIS IS THE STRONGEST SINGLE PIECE OF EVIDENCE AGAINST THE PROTOCOL-DRIFT THESIS AND MUST BE DISCLOSED FIRST.'
 },
 'kurasinski2023': {
  'protocol': 'RANDOM_RESPLIT',
  'headline_accuracy': 99.0,
  'accuracy_kind': 'validation, on the paper’s own 20% slice of the 39,375 training pool',
  'split_sentence_verbatim': "The first dataset is the FLAME dataset [12]... The dataset is 1.18GB in size and contains around 25000 images with fire and 15000 images without fire. || Out of the large dataset containing about 39 000 images, 4598 were TP, 17937 FP, 7082 TN, and finally, 9759 FN. || The validation accuracy is high at almost 100% accuracy and a loss very close to zero. || during validation the model reached 99% which is not too far from the 94% presented in the original work [5].",
  'image_counts': 'the 39,375 training pool only; the 8,617 official test set is never used',
  'other_reported': {'FLAME_to_NASA': 62, 'FLAME_to_GitHub': 60, 'NASA_to_NASA': 92, 'NASA_to_FLAME': 29},
  'within_paper_control': True,
  'comparison_table': True,
  'comparison_rows': "Table 2 “Results achieved from [5]” reproduces the dataset authors' own three numbers verbatim: Test set 0.7414 76.23 | Validation set 0.1506 94.31 | Training set 0.0857 96.79",
  'comparison_protocol_mix': 'compares its own VALIDATION number to Shamsoshoara’s VALIDATION number - like-for-like on the quantity, but never computes the test number',
  'acknowledges_mismatch': 'no - but it is the only paper in the corpus that reproduces all three of Shamsoshoara’s numbers and compares the right pair',
  'evidence_source': 'full text (Springer, retrieved by verification agent and cross-checked against the earlier pass)',
  'verification': 'verified. EARLIEST UNAMBIGUOUS DISCARD of the official test set: 2023-03-14. Its 99% is a validation-split number that a reader will naturally file against 76.23.'
 },
 'islam2023': {
  'protocol': 'K_FOLD_POOLED',
  'split_sentence_verbatim': "The FLAME dataset consists of 39,375 images, with 25,018 representing fire and 14,357 representing non-fire images, all utilized for training. We split these images, dedicating 80% for training (31,500 images) and 20% for validation (7875 images). Furthermore, the dataset contains 8617 images for testing. The model was evaluated on randomly chosen 3000 images from the test set. || In our proposed model, we divided the dataset into four folds of equal size... After four iterations of K-fold cross-validation on the FLAME dataset, the model achieved an accuracy of 97.45%, precision of 98.20%, recall of 97.10%, and an F1-score of 97.12%.",
  'image_counts': '39,375 re-split 80/20 into 31,500/7,875; the 8,617 test set is reduced to “randomly chosen 3000 images”; the headline comes from a four-fold re-partition whose source pool is never stated',
  'accuracy_kind': 'four-fold cross-validation mean (folds 96.78 / 97.29 / 97.23 / 98.53)',
  'comparison_table': True,
  'comparison_rows': "Table 9: Pretrained ResNet50 [27] FLAME 88.00 | Ensemble (EfficientNet-B5, DenseNet-201) [28] FLAME 85.12 | Xception [29] FLAME 76.23 | ResNet50 with DSA [19] FLAME 93.65 | Proposed Model FLAME 97.45 | Proposed Model DeepFire 95.97 (plus two DeepFire-only rows)",
  'comparison_protocol_mix': '4 OFFICIAL FLAME rows + its own K_FOLD_POOLED row in the same accuracy column',
  'acknowledges_mismatch': 'NO',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (forests-14-02080); quotes independently re-verified against that PDF',
  'verification': 'RESOLVED this session - the contested case is settled AGAINST the secondary record. arXiv:2401.02456 records Islam as “Flame1 31,500 8,617 47,992 97.45%”, i.e. as an official-protocol result. That record is WRONG: the paper never evaluates its headline on the 8,617 set. The four fold accuracies span 96.78-98.53, far too tight and too high for the camera-disjoint set. Mowla et al. then import Islam’s 97.45% into their own Table 12 as a FLAME accuracy - the error propagates two hops.'
 },
 'zhang2022': {
  'split_sentence_verbatim': "In this paper, 31501, 7874 and 8617 image samples were extracted from the FLAME data set as the training set, verification set and test set of this experiment, respectively.",
  'image_counts': '31,501 train / 7,874 validation / 8,617 test',
  'other_reported': {'training': 97.14, 'validation': 97.71},
  'within_paper_control': True,
  'comparison_table': False,
  'evidence_source': "full text, MDPI PDF retrieved via mdpi-res.com this session (forests-13-00975). Table 6 verbatim: “Dataset Loss Function Value Accuracy (%) | Training set 0.0612 97.14 | Validation set 0.0398 97.71 | Testing set 0.6823 79.48”. The authors name the cause: “the performance for the test set was relatively lower, reflecting a large domain offset between the test set data and the training and validation data”.",
  'verification': 'verified this session. NEW WITHIN-PAPER CONTROL: validation 97.71 vs test 79.48, an 18.2 point gap, with the mechanism stated by the authors. NOTE: Yan et al. 2022 cite this paper as 77.5% (its augmentation result) while Yar, Yan-FireDA and Zhang-Miao cite it as 79.48% - one source paper, two numbers in circulation.'
 },
 'khan2024': {
  'split_sentence_verbatim': "The FLAME dataset [29], comprising a vast collection of 47,992 images, is divided into 31,501 for training, 7874 for validation, and 8617 for testing. This dataset exhibits a balanced mix, featuring 30,155 (62.8%) images under the Fire category and 17,837 (37.2%) images labeled as No Fire. Specifically, the training subset contains 25,018 Fire and 14,357 No-Fire images, while the testing subset includes 5137 Fire and 3480 No-Fire images for model training and evaluation.",
  'image_counts': '31,501 / 7,874 / 8,617 with correct class counts',
  'comparison_table': True,
  'comparison_rows': "Table 3 lists only its OWN re-trained transfer-learning baselines under its own official split (VGG16 63.98 ... DenseNet121 82.24, FireXplainNet 87.32). Other papers' FLAME numbers appear only in prose.",
  'comparison_protocol_mix': 'none - all rows are the authors’ own runs under one protocol',
  'acknowledges_mismatch': 'not applicable',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (electronics-13-01881)',
  'verification': 'verified this session. Note it gives the correct No-Fire total 17,837, not the propagated 17,855.'
 },
 'zhangmiao2025': {
  'split_sentence_verbatim': "The FLAME dataset consists of 47,992 images, including 30,155 fire images and 17,837 non-fire images... During the data processing, the dataset is divided into a training set and a testing set, with 39,375 images used for training and 8617 images used for testing.",
  'image_counts': '39,375 train / 8,617 test (no validation set defined)',
  'comparison_table': True,
  'comparison_rows': "Table 2: Xception [26] 76.23 | FT-ResNet50 [29] 79.48 | Deep ensemble learning [30] 85.12 | DSAN + ResNet50 [31] 63.9 | ResNet34 86.93% | Single DualArchClassNet 87.97% | The proposed method 89.42%",
  'comparison_protocol_mix': 'ALL ROWS OFFICIAL - protocol-consistent',
  'acknowledges_mismatch': 'not applicable - no mismatch present',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (forests-16-00544)',
  'verification': 'verified this session'
 },
 'yar2026': {
  'split_sentence_verbatim': "The dataset comprises 39,375 labeled training images and 8617 independent test images, with each image annotated as either Fire or No Fire. The training set was further divided into training and validation subsets using an 80:20 split.",
  'image_counts': '39,375 (80:20 train/val) + 8,617 independent test',
  'comparison_table': True,
  'comparison_rows': "Table 6, 19 rows, all in the 51-88% band: Small-Xception 76.23 | Unsupervised DSAN+ResNet50 63.90 | FT-ResNet50 79.48 | Xception 78.41 | EfficientNet-B5 75.82 | B4 69.93 | B3 65.81 | B2 66.04 | InceptionV3 80.88 | DenseNet169 80.62 | MobileNetV3-Small 51.64 | MobileNetV3-Large 65.10 | Ensemble Model 85.12 | DFAN 83.79 | OFAN 84.41 | M-ViTs 84.90 | 2-D CNN (Fixed-point) 81.49 | EFNet-CSM 85.44 | Proposed Model 87.81",
  'comparison_protocol_mix': 'ALL ROWS OFFICIAL - protocol-consistent, and the largest such table in the corpus',
  'acknowledges_mismatch': 'no protocol statement, but it DOES explain the low absolute band structurally: “the Non-Fire class images were acquired within the same forest environment using cropped views of fire-adjacent regions, resulting in visually similar backgrounds shared between the Fire and Non-Fire classes”',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (remotesensing-18-02706)',
  'verification': 'verified this session'
 },
 'yan2022uda': {
  'split_sentence_verbatim': "FLAME is a forest fire dataset collected by UAV in an Arizona pine forest [20]... It is captured by Zenmuse X4S, Phantom 3, both from DJI company (Shenzhen, China), and annotated frame by frame to obtain a training/validation set of 39,375 images and a testing set of 8617 images.",
  'image_counts': 'Table 3: FLAME training set (target) 25,018 / 14,357 labels WITHHELD; FLAME testing set 5,137 / 3,480 labels used',
  'comparison_table': True,
  'comparison_rows': "Table 4: Xception [20] 76.2 | ResNet50 w/SA [38] 77.5 | ToT + ResNet50 (upper bound) 67.5 | ToS + ResNet50 (lower bound) 45.2 | DSAN + ResNet50 63.9",
  'comparison_protocol_mix': 'all OFFICIAL; provenance stated (“The quantitative results of these methods are from [20,21,38]”)',
  'acknowledges_mismatch': 'no protocol statement',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (forests-14-00052)',
  'verification': 'verified this session. Cites Zhang et al. as 77.5% where four other papers cite the same source as 79.48%.'
 },
 'yan2024fireda': {
  'split_sentence_verbatim': "For training and evaluating fire recognition models, the authors segment the dataset into 31,501 training samples, 7874 validation samples, and 8617 testing samples from the visible videos. || Model selection is conducted using the FLAME validation set, and performance is evaluated using the FLAME testing set.",
  'image_counts': 'Table 1: FLAME training set (target) 20,015/11,486 labels withheld; validation 5,003/2,871; testing 5,137/3,480',
  'other_reported': {'validation': 96.3, 'F1': 81.39, 'recall': 79.4, 'precision': 83.48},
  'comparison_table': True,
  'comparison_rows': "Table 6: Xception [93] 76.23 | ResNet50+SA [66] 79.48 | ToT+ResNet50 [61] 67.50 | DSAN+ResNet50 [61] 63.90 | Our model 78.36",
  'comparison_protocol_mix': 'ALL ROWS OFFICIAL - protocol-consistent',
  'acknowledges_mismatch': 'it adds a METRIC-level caveat (“Because references [66,93] have not made their codes publicly available and reported only recognition accuracy, our comparison primarily focuses on this metric”) but no protocol/split statement',
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com this session (forests-15-01684). Validation 96.30 in Table 4 (“Ablation study... on the FLAME validation set”); test 78.36 in Table 6.',
  'verification': 'verified this session. WITHIN-PAPER CONTROL confirmed: 96.30 validation vs 78.36 test, adjacent tables, no remark.'
 },
 'deng2025': {
  'pub_date': '2025-02-28',
  'date_precision': 'day',
  'split_sentence_verbatim': "In this study, the FLAME database (Shamsoshoara et al. 2021) is used. Specifically, a subset of 39,375 RGB frame images, captured by the Zenmuse X4S camera, is employed for training. This subset comprises 25,018 “fire” samples and 14,357 “non-fire” samples. The test data set consists of 8,617 images captured by a Phantom 3 camera, with 5,137 “fire” samples and 3,480 “non-fire” samples, respectively.",
  'image_counts': '39,375 train (Zenmuse X4S) / 8,617 test (Phantom 3) - the only paper in the corpus that names both cameras in its split sentence',
  'other_reported': {'mean_of_30_models': 85.82, 'three_voter': 87.36, 'single_MV2_CBAM': 90.62,
                     'second_dataset_random_60_40': 88.83},
  'within_paper_control': True,
  'comparison_table': True,
  'comparison_rows': "Table 3: Shamsoshoara et al. (2021) 76.23% | Ghali et al. (2022) 85.12% | Zhang Wang et al. (2022) 79.48% | Average of 30 MV2-CBAM models 85.82% | Three-voter ensemble 87.36% | Five-voter ensemble 88.05%",
  'comparison_protocol_mix': 'ALL ROWS OFFICIAL - protocol-consistent, and it is the ONLY paper in the corpus that explicitly asserts comparability: “The same training and test data sets have been evaluated using Xception (Shamsoshoara et al. 2021), ResNet50 (Zhang Wang et al. 2022), and ensemble EfficientNet-B5 and DenseNet201 (Ghali et al. 2022). For comparison, the published results are extracted from the literature and presented in Table 3.”',
  'acknowledges_mismatch': 'it asserts there is none - and on these four rows it is correct',
  'evidence_source': 'full text (Springer, retrieved by verification agent)',
  'verification': 'verified. WITHIN-PAPER CONTROL, but a WEAK one that runs AGAINST the thesis: official FLAME 88.05 vs a random 60/40 split of a second 1,204-image dataset at 88.83 - a 0.8 point gap, not a 15-20 point gap. The second dataset is different data, so this is not a clean control, but a reviewer will cite it.'
 },
 'mowla2025': {
  'pub_date': '2024-12-30',
  'date_precision': 'day',
  'year': 2024,
  'split_sentence_verbatim': "The dataset was divided into training and test sets, with the training set containing 14,357 instances of no-fire and 25,018 instances of fire data. In comparison, the test set comprised 3,480 instances of no-fire and 5,137 instances of fire data. || In this, we merged the train and test folders into a single directory, resulting in a total dataset size of 47,992 entries. We utilized a total of 35,600 images for this research. || For the UAVsFFDB dataset, data partitioning involved allocating 80% for training, 10% for validation, and 10% for testing, while for the FLAME dataset, the split was adjusted to 85% for training, 10% for validation, and 5% for testing.",
  'comparison_table': True,
  'comparison_rows': "Table 12: Shamsoshoara et al. Xception FLAME 76.23% | Majid et al. 95.40% | Islam et al. EfficientNetB7+ACNet FLAME/DeepFire 97.45% | Dilshad et al. 96.54% | Aral et al. FLAME 92.02% | Zhang et al. 98.90% | Yu et al. 96.19% mAP | Kong et al. ADE-Net FLAME 83.80% | Li et al. 80.92% mAP | Yar et al. 98.65/93.51/90.63% | Li et al. 99.06% | Wang et al. F1 87.2%",
  'comparison_protocol_mix': 'mixes OFFICIAL FLAME rows (Shamsoshoara 76.23, Kong 83.80) with its own merged-pool re-split, with Islam’s four-fold cross-validation mean (97.45), and with rows measured on entirely different datasets',
  'acknowledges_mismatch': 'NO',
  'evidence_source': 'full text via a text-extraction proxy over IEEE Xplore (agent-retrieved). MARKED: this is the only paper in the set whose quotes were not rendered and read directly; treat as high-confidence but not eyeball-verified against the publisher PDF.',
  'verification': 'verified in the earlier pass and re-confirmed by the agent. Date CORRECTED to 2024-12-30 (Unpaywall and OpenAlex agree); the IEEE Access volume assignment is 13 (2025), which is why an earlier note said 2025. NOTE the paper reports 99.83 / 99.10 / 99.33 for three variants and its own abstract says 99.32 where the body says 99.33 - a small internal inconsistency.'
 },
 'ghali2022': {
  'other_reported': {'segmentation_F1_abstract': 99.9, 'note': 'the 99.90 in the abstract is SEGMENTATION F1, not classification accuracy'}
 }
}

for k, v in PATCH.items():
    if k not in IDX:
        print('MISSING id', k); continue
    IDX[k].update(v)

json.dump(rows, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('patched', len(PATCH), 'entries;', len(rows), 'rows total')
