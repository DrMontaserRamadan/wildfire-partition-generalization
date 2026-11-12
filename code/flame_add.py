"""Append the 2026-09-09 discovery-pass papers to corpus/flame_timeline.json."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = os.path.join(ROOT, 'corpus', 'flame_timeline.json')
rows = json.load(open(P, encoding='utf-8'))
have = {r['id'] for r in rows}

AG = ('AGENT-RETRIEVED via an IEEE Xplore institutional session; DOI, authors and date confirmed '
      'against Crossref on this machine, but the quoted text was NOT independently re-read here. '
      'Treat the quote as high-confidence, not eyeball-verified.')

NEW = [
 {'id': 'dutta2021', 'first_author': 'Dutta', 'authors': 'Dutta, Ghosh', 'year': 2021,
  'pub_date': '2021-04-06', 'date_precision': 'day', 'venue': 'IEEE CAIDA 2021',
  'doi': '10.1109/CAIDA51941.2021.9425170',
  'split_sentence_verbatim': "The study's dataset was obtained from IEEE DataPort, which contains UAV captured aerial imageries from prescribed pile burn from Northern Arizonian pine forest in the US [14]. The contributing authors assembled the static repositories containing training/validation dataset and test dataset images by preprocessing the in-situ video data. || Training the selected simple CNN model on Google Colab Pro with 39375 images required eleven epochs... the model performance was evaluated on a standard windows i5 system which required a computation time of 151 seconds while testing the model on 8608 images.",
  'image_counts': '39,375 train; 8,608 test (NINE FRAMES SHORT of the official 8,617 - unexplained)',
  'protocol': 'OFFICIAL', 'headline_accuracy': 92.0, 'accuracy_kind': 'test',
  'other_reported': {'sensitivity': 91.26, 'specificity': 92.51},
  'within_paper_control': False, 'comparison_table': False,
  'evidence_source': AG + ' Quoted diagnosis of the field: "Even though each of these algorithms training accuracy was greater than 99%, the test set (or validation) accuracy hardly crossed 79%." Method is a separable CNN plus HSV thresholding/segmentation pre-processing, not a larger backbone.',
  'verification': '*** THESIS-CRITICAL AND NOT INDEPENDENTLY VERIFIED. *** If this is a genuine official-protocol result at 92.0%, it raises the official-band ceiling from 89.42 to 92.00 and shrinks the empty space between the protocol bands from 4.23 points to 1.65. It also predates every other entry except Shamsoshoara. RESOLVE BEFORE ANY CLAIM OF BAND SEPARATION. The 8,608-vs-8,617 discrepancy needs explaining too.'},

 {'id': 'li2022rshuffle', 'first_author': 'Li', 'authors': 'Li, Zhang, Mu, Xin, Xue, Jiao, Liu, Xie, Yi',
  'year': 2022, 'pub_date': '2022-04-08', 'date_precision': 'day', 'venue': 'IEEE ISAS 2022',
  'doi': '10.1109/ISAS55863.2022.9757053',
  'split_sentence_verbatim': "The dataset contains 47,992 images, divided into train set and test set. Images on the train set were acquired using a DJI Matrice 200 UAV and Zenmouse X4S camera, and images on the test dataset were acquired using a DJI Phantom 3 UAV and its default camera. There is no overlap between training samples and test samples.",
  'image_counts': '47,992 total, official train/test division, both cameras named',
  'protocol': 'OFFICIAL', 'headline_accuracy': 86.33, 'accuracy_kind': 'test',
  'other_reported': {'train': 99.63, 'F1': 0.8908,
                     'shufflenetv2_baseline_train': 99.81, 'shufflenetv2_baseline_test': 82.12},
  'within_paper_control': True, 'comparison_table': False,
  'evidence_source': AG + ' Table II verbatim: "Performance Accuracy (%) F1 Score Running speed | Train set Test set | shufflenetv2 99.81 82.12 0.8544 34 FPS | r-shufflenetv2 99.63 86.33 0.8908 31 FPS".',
  'verification': 'agent-retrieved. WITHIN-PAPER CONTROL: train 99.63 vs official test 86.33 = 13.3 points, printed by the authors in one row.'},

 {'id': 'li2022cghost', 'first_author': 'Li', 'authors': 'Li, Zhang, Mu, Xin, Yu, Jiao, Liu, Xie, Yi',
  'year': 2022, 'pub_date': '2022-04-08', 'date_precision': 'day', 'venue': 'IEEE ISAS 2022',
  'doi': '10.1109/ISAS55863.2022.9757318',
  'split_sentence_verbatim': "The FLAME dataset contains 47,992 images, which are divided into train set and test set [16]. Train set contains 39,375 images, including 25,018 fire images and 14,357 images without fire. Test dataset consists of 8,617 images, including 5,137 fire images and 3,480 images without fire. The images on the train set are collected by using the DJI Matrice 200 UAV and the Zenmouse X4S camera, and the images on the test dataset are collected by using the DJI Phantom 3 UAV and its default camera. There is no overlap between training samples and test samples.",
  'image_counts': '39,375 (25,018/14,357) + 8,617 (5,137/3,480) - the most complete official restatement in the corpus',
  'protocol': 'OFFICIAL', 'headline_accuracy': 82.30, 'accuracy_kind': 'test',
  'other_reported': {'train': 99.82, 'F1': 0.8650,
                     'ghostnet_baseline_train': 99.77, 'ghostnet_baseline_test': 77.16},
  'within_paper_control': True, 'comparison_table': False,
  'evidence_source': AG + ' Table II verbatim: "Performance Accuracy (%) F1 score | Train set Test set | GhostNet 99.77 77.16 0.8302 | C-GhostNet 99.82 82.30 0.8650".',
  'verification': 'agent-retrieved. WITHIN-PAPER CONTROL: train 99.82 vs official test 82.30 = 17.5 points. With its sister paper above, the cleanest non-Shamsoshoara pair in the corpus.'},

 {'id': 'namburu2023', 'first_author': 'Namburu',
  'authors': 'Namburu, Selvaraj, Mohan, Ragavanantham, Tag Eldin', 'year': 2023,
  'pub_date': '2023-02-01', 'date_precision': 'day', 'venue': 'Electronics 12(3):733',
  'doi': '10.3390/electronics12030733',
  'split_sentence_verbatim': "Images were collected using the designed UAV, and images were extracted from videos of forest fires collected in kaggle and FLAME; then, we added frames from videos taken with the drone. The dataset was divided into two parts: fire and non-fire. This fire dataset contains a total of 5313 fire images, and the non-fire dataset contains a total of 677 images. || The method used 65 percent of images for training and 35 percent of images for testing.",
  'image_counts': '5,313 fire + 677 non-fire, drawn from Kaggle + FLAME + the authors own drone; 65/35 split',
  'protocol': 'SUBSET_OF_UNCLEAR_PROVENANCE', 'headline_accuracy': 97.22,
  'accuracy_kind': 'validation (Table 3: Training 0.9793 / Validation 0.9722)',
  'other_reported': {'agent_claimed_table5': '98.89 - NOT FOUND in the PDF text layer, NOT USED'},
  'within_paper_control': False, 'comparison_table': None,
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com and read on this machine (electronics-12-00733). The 5,313/677 counts, the 65/35 split and the 97.22 figure were all CONFIRMED here.',
  'verification': 'PARTIALLY CORRECTED. The discovery agent reported a headline of 98.89% from "Table 5"; that string does not occur in the PDF text layer and is NOT used. The verified figure is 97.22%. CAVEAT: the word FLAME occurs ONCE in the whole paper and the pool mixes three sources, so this is a contaminated-pool case, not a FLAME re-split. Consider excluding it from the FLAME timeline entirely.'},

 {'id': 'wang2023access', 'first_author': 'Wang', 'authors': 'Wang, Zhang, Zhang, Hu, An',
  'year': 2023, 'pub_date': '2023-03-28', 'date_precision': 'day',
  'venue': 'IEEE Access 11:32671-32681', 'doi': '10.1109/ACCESS.2023.3262701',
  'split_sentence_verbatim': "In order to verify our experiment, we used the dataset from FLAME, a forest wildfire dataset opened by Northern Arizona University [30]. A total of 900 consecutive images of wildfire flames were collected as positive samples and 1000 non-flame images were collected as negative samples from FLAME. We divided the dataset into three parts, which are training set, validation set and testing set.",
  'image_counts': '1,900 hand-picked FLAME images (900 fire + 1,000 non-fire); the positives are CONSECUTIVE video frames',
  'protocol': 'SUBSET_OF_UNCLEAR_PROVENANCE', 'headline_accuracy': 91.20,
  'accuracy_kind': 'test on its own split',
  'other_reported': {}, 'within_paper_control': False, 'comparison_table': None,
  'evidence_source': AG,
  'verification': 'agent-retrieved. IN THE 90-97 BAND. "900 consecutive images" is the whole diagnosis: adjacent video frames split at random. No camera, flight or ratio stated.'},

 {'id': 'deng2023prml', 'first_author': 'Deng', 'authors': 'Deng, Khan, Lim, Liao', 'year': 2023,
  'pub_date': '2023-08-04', 'date_precision': 'day', 'venue': 'IEEE PRML 2023',
  'doi': '10.1109/PRML59573.2023.10348345',
  'split_sentence_verbatim': "A total of 39,375 RGB frames recorded by Zenmuse X4S are used for training, validation and test, including 25,018 and 14,357 samples labeled as \"fire\" and \"non-fire\", respectively. The test data set has 8,617 frames recorded by Phantom 3 camera, with 5,137 and 3,480 samples of \"fire\" and \"non-fire\" images respectively.",
  'image_counts': '39,375 + 8,617, official, both cameras named',
  'protocol': 'OFFICIAL', 'headline_accuracy': 86.14, 'accuracy_kind': 'test',
  'other_reported': {'F1': 0.8719}, 'within_paper_control': False, 'comparison_table': None,
  'evidence_source': AG,
  'verification': 'agent-retrieved. Same group as Deng et al. Soft Computing 2025 (88.05). Official protocol held constant across two years: 86.14 -> 88.05.'},

 {'id': 'zachariadis2023', 'first_author': 'Zachariadis',
  'authors': 'Zachariadis, Antonakakis, Zervakis', 'year': 2023, 'pub_date': '2023-10-17',
  'date_precision': 'day', 'venue': 'IEEE IST 2023', 'doi': '10.1109/IST59124.2023.10355703',
  'split_sentence_verbatim': "This repository contains 39,375 RGB frames of forest fires, captured from a UAV, with 254px254p resolution that are used for the training and validation procedure with a split ratio of 80/20. Additionally, it provides 8,617 RGB frames with the same resolution, that are used as a test dataset for our \"Fire-vs-No Fire\" image classification problem. || We took the proposed structure (ShRe-Xception), trained it with 40 epochs and tested it on the combined dataset. The best results came at 24th epoch where the network hit a testing accuracy of 90.10%.",
  'image_counts': 'FLAME arm 39,375 + 8,617; plus a merged FLAME+FLAME2 pool of 87,486 train/val and 13,965 test',
  'protocol': 'INTERNALLY_INCONSISTENT', 'headline_accuracy': None,
  'accuracy_kind': 'the 90.10% headline is on a merged FLAME+FLAME2 pool, NOT on FLAME; excluded from the trend for that reason',
  'other_reported': {'official_flame_replication_of_xception': 73.16, 'headline_on_merged_pool': 90.10},
  'within_paper_control': True, 'comparison_table': None,
  'evidence_source': AG + ' Verbatim: "we took the same network structure and after training it on the same dataset that the authors did [1], we tested it, accomplishing an accuracy of 73.16% (Table II)."',
  'verification': 'agent-retrieved. POSSIBLY THE BEST SINGLE SPECIMEN IN THE CORPUS: one paper, one task, one team - 73.16% on the official FLAME test set (3 points BELOW the 76.23 they were reproducing, an independent replication shortfall) and 90.10% once FLAME2 is merged in and the split is redrawn. The number moves 17 points on a change of test set alone.'},

 {'id': 'arunkumar2024', 'first_author': 'Arunkumar', 'authors': 'Arunkumar, Dubey', 'year': 2024,
  'pub_date': '2024-07-02', 'date_precision': 'day', 'venue': 'IEEE COMPSAC 2024',
  'doi': '10.1109/COMPSAC61105.2024.00260',
  'split_sentence_verbatim': "The dataset consisted of a total of 8617 images, where there were 5137 images in the Fire category and 3480 images in the No_Fire category. The dataset was split into disjoint train, validation and test subsets. Specifically, 80% of the images were allocated to the training subset to train the model, while the remaining 20% was equally divided, with 10% in validation and another 10% in testing.",
  'image_counts': 'the 8,617-frame OFFICIAL TEST SET, re-split 80/10/10; the 39,375 training pool is never used',
  'protocol': 'RANDOM_RESPLIT', 'headline_accuracy': 98.10,
  'accuracy_kind': 'test on its own re-split of the official test set',
  'other_reported': {'validation': 99.4}, 'within_paper_control': False, 'comparison_table': None,
  'evidence_source': AG + ' The paper cites the anchor: "Previous work utilizing this dataset has yielded notable advancements, such as an Artificial Neural Network achieving a 76% accuracy in binary classification" - then reports 98.1% with no protocol remark.',
  'verification': 'agent-retrieved. A NEW FAILURE MODE not previously in our taxonomy: the camera-disjoint TEST SET is itself shuffled and re-split, so train and test come from the same Phantom-3 flight. It is the only paper in the corpus that discards the TRAINING pool rather than the test set.'},

 {'id': 'li2024firenet', 'first_author': 'Li', 'authors': 'Li, Han, Chen, Min, Yi, Yang',
  'year': 2024, 'pub_date': '2024-08-02', 'date_precision': 'day',
  'venue': 'Remote Sensing 16(15):2846', 'doi': '10.3390/rs16152846',
  'split_sentence_verbatim': "Therefore, we made several improvements to the FLAME aerial forest fire dataset [24]. First, redundant fire images were removed through interval sampling. Second, different types of fire images and some easily 'confusable' images were downloaded from the internet (ensuring no copyright issues) and integrated into the dataset... Ultimately, our dataset consists of 7666 original images, with a 2:3 ratio of positive to negative samples. The dataset is partitioned into training, validation, and test sets, at a proportion of 8:1:1.",
  'image_counts': '7,666 images - FLAME interval-subsampled and mixed with internet images; split 8:1:1',
  'protocol': 'SUBSET_OF_UNCLEAR_PROVENANCE', 'headline_accuracy': 98.18,
  'accuracy_kind': 'test on its own split',
  'other_reported': {'precision': 99.14, 'recall': 98.01, 'ablation_original_dataset_only': 93.45,
                     'ablation_plus_ambiguous': 94.62, 'ablation_both': 94.18},
  'within_paper_control': False, 'comparison_table': None,
  'evidence_source': 'full text, MDPI PDF retrieved via mdpi-res.com and read on this machine (remotesensing-16-02846). All quoted figures CONFIRMED here.',
  'verification': 'VERIFIED ON THIS MACHINE. Useful for a second reason: its own ablation moves accuracy from 93.45% to 94.18% purely by changing DATASET COMPOSITION with the architecture fixed - the authors document that the number is a property of the data, not the model.'},

 {'id': 'lehong2024', 'first_author': 'Le Hong', 'authors': 'Le Hong, Zhao', 'year': 2024,
  'pub_date': '2024-12-15', 'date_precision': 'day', 'venue': 'IEEE BigData 2024',
  'doi': '10.1109/BigData62323.2024.10825113',
  'split_sentence_verbatim': "OCC was applied on FLAME and FLAME2. For each dataset, a subsample rate of 1% was used due to the similar nature of many of the images. || Since a subsample was taken due to the similar nature of images in the dataset, the resulting FLAME dataset only contained 172 non-fire images and 53 fire images.",
  'image_counts': '225 images (172 non-fire + 53 fire) - a 1% subsample',
  'protocol': 'SUBSET_OF_UNCLEAR_PROVENANCE', 'headline_accuracy': None,
  'accuracy_kind': 'no accuracy reported; F1 = 0.94 only. EXCLUDED from the trend.',
  'other_reported': {'F1': 0.94}, 'within_paper_control': False, 'comparison_table': None,
  'evidence_source': AG + ' Cross-dataset diagnosis, verbatim: "An experiment was conducted where a model was trained on the FLAME data set and tested on only the FLAME 2 data set. Figure 1 shows that while the training accuracy is high, there is no noticeable change in the testing accuracy... the model is not accurately learning what a wildfire is."',
  'verification': 'agent-retrieved. Carried for its explicit statement of the near-duplicate problem ("the similar nature of many of the images" forced a 1% subsample), which independently corroborates the frame-redundancy premise.'},
]

added = 0
for r in NEW:
    if r['id'] in have:
        continue
    rows.append(r)
    added += 1
rows.sort(key=lambda r: (r['pub_date'] or 'zzz'))
json.dump(rows, open(P, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('added', added, '| total rows', len(rows))
