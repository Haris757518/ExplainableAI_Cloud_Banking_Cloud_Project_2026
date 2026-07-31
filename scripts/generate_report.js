const fs = require("fs");
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell,
  WidthType, ShadingType, AlignmentType, BorderStyle, PageBreak, LevelFormat,
  convertInchesToTwip, VerticalAlign, PageNumber, Footer, Header
} = require("docx");

const FONT = "Calibri";
const ACCENT = "1F4E79";
const LIGHT = "DDEBF7";

function H1(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 150 } });
}
function H2(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } });
}
function H3(text) {
  return new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 180, after: 90 } });
}
function P(text, opts = {}) {
  return new Paragraph({
    children: [new TextRun({ text, font: FONT, size: 22, bold: opts.bold, italics: opts.italics })],
    spacing: { after: 140 },
    alignment: opts.align,
  });
}
function Lbl(label, value) {
  return new Paragraph({
    children: [
      new TextRun({ text: label + ": ", bold: true, font: FONT, size: 22 }),
      new TextRun({ text: value, font: FONT, size: 22 }),
    ],
    spacing: { after: 100 },
  });
}
function bullet(text, level = 0) {
  return new Paragraph({
    children: [new TextRun({ text, font: FONT, size: 22 })],
    bullet: { level },
    spacing: { after: 90 },
  });
}
function refPara(text) {
  return new Paragraph({
    children: [new TextRun({ text, font: FONT, size: 20 })],
    spacing: { after: 120 },
    indent: { left: 360, hanging: 360 },
  });
}

function cell(text, opts = {}) {
  return new TableCell({
    width: { size: opts.width || 2000, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: ACCENT } : (opts.shade ? { type: ShadingType.CLEAR, fill: LIGHT } : undefined),
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 80, bottom: 80, left: 100, right: 100 },
    children: [new Paragraph({
      children: [new TextRun({ text, font: FONT, size: opts.size || 19, bold: opts.header, color: opts.header ? "FFFFFF" : undefined })],
    })],
  });
}

function simpleTable(headers, rows, widths) {
  const totalWidth = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: totalWidth, type: WidthType.DXA },
    columnWidths: widths,
    rows: [
      new TableRow({
        tableHeader: true,
        children: headers.map((h, i) => cell(h, { header: true, width: widths[i] })),
      }),
      ...rows.map((r, ri) => new TableRow({
        children: r.map((c, i) => cell(c, { width: widths[i], shade: ri % 2 === 1 })),
      })),
    ],
  });
}

// ---------- Title Page ----------
const titlePage = [
  new Paragraph({ spacing: { before: 1200 }, children: [] }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "PROJECT PHASE-I REPORT", font: FONT, size: 28, bold: true, color: ACCENT })],
    spacing: { after: 400 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({
      text: "Explainable, Camouflage-Resistant, Imbalance-Aware Graph Neural Networks for Cloud-Native Digital Banking Fraud Detection and Performance Analytics",
      font: FONT, size: 30, bold: true,
    })],
    spacing: { after: 500 },
  }),
  new Paragraph({
    alignment: AlignmentType.CENTER,
    children: [new TextRun({ text: "BCSE355L — Cloud Architecture Design", font: FONT, size: 24, italics: true })],
    spacing: { after: 800 },
  }),
];

function titleInfoTable() {
  const rows = [
    ["Course Name", "BCSE355L – Cloud Architecture Design"],
    ["Instructor Name", "Dr. Priya V"],
    ["Team Members", "Haris K, Keshav Gokaram, Harish Kumar"],
    ["Register Numbers", "[Fill in — e.g., 21BITxxxx, 21BITxxxx, 21BITxxxx]"],
    ["Date", "31 July 2026"],
  ];
  return new Table({
    width: { size: 9000, type: WidthType.DXA },
    columnWidths: [3000, 6000],
    rows: rows.map((r, i) => new TableRow({
      children: [cell(r[0], { header: false, width: 3000, size: 22, shade: true }), cell(r[1], { width: 6000, size: 22 })],
    })),
  });
}

// ---------- Abstract ----------
const abstract = P(
  "Digital banking platforms process millions of transactions daily across accounts, cards, merchants, and devices, forming a naturally graph-structured environment in which fraud, money laundering, and infrastructure anomalies manifest as suspicious relational patterns rather than isolated feature outliers. Traditional rule-based and tabular machine learning fraud detectors struggle to capture these multi-entity relationships, are brittle to fraudsters who deliberately camouflage their behavior, and offer little transparency to regulators and compliance auditors who must justify each flagged decision. This project proposes an explainable, cloud-native Graph Neural Network (GNN) platform for digital banking that unifies four capabilities rarely combined in existing literature: adversarial robustness against camouflaged fraud behavior, structured handling of extreme class imbalance, dynamic adaptation to continuously evolving transaction graphs, and native explainability suited to regulatory audit requirements. Building on a systematic review of fifteen peer-reviewed and recent research articles spanning GNN-based fraud detection, cloud infrastructure anomaly detection, and explainable AI, the project identifies a consistent gap: no single reviewed system integrates real-time low-latency inference, privacy-aware federated learning, deep XAI-based regulatory auditing, and class-imbalance resilience within one cloud-native microservice architecture. The proposed system addresses this gap through a tiered AWS-based cloud architecture combining a fast inline GNN inference path for live transaction scoring with an asynchronous explainability and compliance-auditing pipeline. Key design elements informed by the literature include a camouflage-resistant multi-relation neighbor selector, a label-balanced graph sampler for imbalance handling, a weight-evolution mechanism for dynamic graph adaptation, and an attention/SHAP-based explainability layer. The system is intended to be evaluated on public fraud benchmarks (Yelp, Amazon, Elliptic, IEEE-CIS) alongside synthetic transaction graphs, with performance measured via AUC-ROC, F1, G-Mean, and inference latency. This Phase-I report documents the literature foundation, identified research gaps, novelty positioning, proposed cloud architecture, dataset plan, AWS service mapping, and team work distribution guiding the subsequent implementation phase."
);

// ---------- Problem Statement ----------
const problemStatement = [
  P("Digital banking fraud detection faces four compounding challenges that existing systems address only in isolation. First, fraudsters actively camouflage their behavior to mimic legitimate transaction patterns, evading detectors that assume benign neighborhoods in the transaction graph. Second, fraudulent transactions represent a tiny minority of overall traffic (often below 1%), causing standard learning algorithms to bias toward the majority legitimate class. Third, digital banking graphs are inherently dynamic — new accounts, cards, and merchant relationships are created continuously, and static graph models become stale without costly full retraining. Fourth, regulatory frameworks (RBI guidelines, PCI-DSS, GDPR-equivalent norms) require that any automated fraud or risk decision be explainable to compliance officers and auditors, yet most high-performing GNN fraud detectors operate as opaque black boxes."),
  P("There is currently no unified, cloud-deployable system that simultaneously resolves adversarial camouflage, class imbalance, temporal graph evolution, and regulatory-grade explainability within a single low-latency architecture suitable for live digital banking transaction pipelines. This project addresses that gap by proposing an explainable, cloud-native GNN-based fraud detection and cloud performance analytics platform for digital banking."),
];

// ---------- Objectives ----------
const objectives = [
  "Design a camouflage-resistant, multi-relation GNN fraud detection module capable of filtering adversarially disguised fraudulent connections in transaction graphs.",
  "Develop a class-imbalance-aware training pipeline using structured graph sampling to reliably detect rare fraudulent transactions without excessive false positives.",
  "Implement a dynamic graph adaptation mechanism that incorporates new accounts, cards, and relationships into the model without full retraining.",
  "Build a native explainability layer (attention-based and/or SHAP-based) that generates human-readable, regulator-facing justifications for each flagged transaction.",
  "Architect and deploy a tiered, low-latency AWS cloud infrastructure that separates real-time inline fraud scoring from asynchronous compliance auditing and reporting.",
  "Evaluate the proposed system against established public benchmarks (Yelp, Amazon, Elliptic, IEEE-CIS) using AUC-ROC, F1, G-Mean, and inference latency as comparison metrics against baseline GNN and non-GNN detectors.",
];

// ---------- Literature Survey papers data ----------
const member1papers = [
  {
    num: 1, title: "Enhancing Graph Neural Network-based Fraud Detectors against Camouflaged Fraudsters (CARE-GNN)",
    ref: "Dou, Y., Liu, Z., Sun, L., Deng, Y., Peng, H., & Yu, P. S. (2020). Enhancing Graph Neural Network-based Fraud Detectors against Camouflaged Fraudsters. Proc. 29th ACM Int. Conf. Information and Knowledge Management (CIKM '20), 315–324.",
    objective: "Improve GNN-based fraud detection by explicitly countering fraudster \u201ccamouflage\u201d — the deliberate mimicking of benign behavior to evade detection.",
    methodology: "A multi-relation graph fraud detector with three modules: a label-aware similarity measure to identify informative neighbors, a reinforcement-learning-based neighbor selector that chooses the optimal number of neighbors per relation, and a cross-relation aggregator.",
    dataset: "Yelp spam reviews (~45,954 nodes, 3 relations) and Amazon fraud (~11,944 nodes, 3 relations).",
    findings: [
      "Outperforms GCN, GraphSAGE, and prior GNN fraud detectors in ROC-AUC and Recall on both datasets.",
      "The RL neighbor selector adaptively filters out noisy, camouflaged connections during training.",
      "Establishes feature camouflage and relation camouflage as two distinct adversarial behaviors.",
    ],
    limitations: ["Designed for static, multi-relation graphs; does not model transaction timing.", "No built-in explainability layer."],
    relevance: "Establishes a concrete mechanism for handling adversarial camouflage in banking graphs, directly supporting the robustness requirements of the proposed fraud-detection module.",
  },
  {
    num: 2, title: "Pick and Choose: A GNN-based Imbalanced Learning Approach for Fraud Detection (PC-GNN)",
    ref: "Liu, Y., Ao, X., Qin, Z., Chi, J., Feng, J., Yang, H., & He, Q. (2021). Pick and Choose: A GNN-based Imbalanced Learning Approach for Fraud Detection. Proc. Web Conference (WWW '21), 3168–3177.",
    objective: "Address the severe class imbalance inherent in transaction fraud graphs without simply oversampling or undersampling raw data.",
    methodology: "A label-balanced sampler selects nodes and edges to construct balanced subgraphs during training, paired with a neighborhood-choosing module that adaptively picks informative neighbors and under-samples majority-class connections during message passing.",
    dataset: "Yelp and Amazon fraud benchmark datasets, plus a real financial fraud dataset from a partner platform.",
    findings: [
      "Consistently improves AUC, F1, and G-Mean over CARE-GNN under high imbalance ratios.",
      "The label-balanced sampler mitigates majority-class bias more effectively than random resampling.",
      "Neighborhood-choosing generalizes across relation types without manual tuning.",
    ],
    limitations: ["Sampling adds training-time overhead.", "Treats the transaction graph as a single static snapshot."],
    relevance: "Provides a directly applicable technique for the class-imbalance problem central to banking fraud detection, informing the sampling strategy of the proposed training pipeline.",
  },
  {
    num: 3, title: "EvolveGCN: Evolving Graph Convolutional Networks for Dynamic Graphs",
    ref: "Pareja, A., Domeniconi, G., Chen, J., Ma, T., Suzumura, T., Kanezashi, H., Kaler, T., Schardl, T., & Leiserson, C. (2020). EvolveGCN. Proc. AAAI Conference on Artificial Intelligence, 34(04), 5363–5370.",
    objective: "Model graphs that change structure and node population over time without relying on fixed node embeddings that become stale.",
    methodology: "A recurrent network (GRU/LSTM) evolves the GCN's own weight matrices at each time step, rather than the node embeddings directly, allowing generalization to unseen nodes at inference time.",
    dataset: "Link prediction, edge classification, and node classification benchmarks, including the Elliptic Bitcoin transaction graph.",
    findings: [
      "Outperforms static GCN/GAT baselines on the Elliptic financial transaction dataset.",
      "Handles entirely new nodes at test time, unlike embedding-evolution approaches.",
      "Two variants (GRU vs. LSTM) trade off responsiveness against stability.",
    ],
    limitations: ["Not designed with anomaly detection as the primary objective.", "No explainability mechanism."],
    relevance: "Supplies a parameter-evolution mechanism essential for a live digital-banking transaction graph, where new accounts and relationships are continuously added.",
  },
  {
    num: 4, title: "Semi-Supervised Credit Card Fraud Detection via Attribute-Driven Graph Representation (GTAN)",
    ref: "Xiang, S., Zhu, M., Cheng, D., Li, E., Zhao, R., Ouyang, Y., Chen, L., & Zheng, Y. (2023). Proc. AAAI Conference on Artificial Intelligence, 37(12), 14557–14565.",
    objective: "Improve credit card fraud detection when most transaction labels are unavailable, common in real banking pipelines.",
    methodology: "Constructs a transaction graph and generates pseudo node attributes via a gated temporal attention module; a risk propagation step spreads label information from a small labeled set to unlabeled neighbors, refined through semi-supervised graph attention learning.",
    dataset: "Large-scale industrial credit card transaction dataset from a partner bank, plus public Amazon and Yelp benchmarks.",
    findings: [
      "Outperforms fully-supervised GNN fraud baselines despite using only a small fraction of labeled data.",
      "The gated temporal attention module captures short-term behavioral bursts.",
      "Strong performance retention even below 10% labeled data.",
    ],
    limitations: ["Depends on quality of the initial labeled set.", "Attention module adds inference latency."],
    relevance: "Addresses the practical constraint that most real banking transactions arrive unlabeled, directly relevant to a deployable digital-banking fraud system.",
  },
  {
    num: 5, title: "AddGraph: Anomaly Detection in Dynamic Graphs via Attention-based Temporal GCN",
    ref: "Zheng, L., Li, Z., Li, J., Li, Z., & Gao, J. (2019). AddGraph. Proc. 28th IJCAI, 4419–4425.",
    objective: "Detect anomalous edges as they appear in a continuously evolving graph, rather than only classifying entire graph snapshots.",
    methodology: "Combines a GCN for structural context, a GRU with attention for short- and long-term temporal patterns, and a negative-sampling scheme generating synthetic anomalous edges to avoid requiring large labeled anomaly sets.",
    dataset: "UCI messages, Digg, and a bitcoin-alpha trust network, plus synthetic anomaly injection.",
    findings: [
      "Outperforms static anomaly baselines and prior dynamic graph anomaly methods in AUC.",
      "Attention over historical snapshots distinguishes anomalous edges from normal bursty activity.",
      "Requires substantially fewer labeled anomalies than fully supervised alternatives.",
    ],
    limitations: ["Snapshot-based processing introduces detection lag.", "No explainability component."],
    relevance: "Applies temporal graph anomaly detection to edge-level financial interactions, reinforcing the case for temporal, explainable fraud detection.",
  },
];

const member2papers = [
  {
    num: 6, title: "GAL-MAD: Towards Explainable Anomaly Detection in Microservice Applications Using Graph Attention Networks",
    ref: "Akmeemana, L., Faiz, H., Attanayake, C., & Wickramanayake, S. (2025). arXiv:2504.00058. University of Moratuwa, Sri Lanka.",
    objective: "Detect anomalies in cloud-hosted microservice applications by jointly modeling structural dependencies and temporal behavior, then explain each anomaly at the service/metric level.",
    methodology: "Unsupervised encoder-decoder autoencoder: two GAT layers followed by a Bidirectional LSTM capture spatial and temporal dependencies; trained on normal telemetry only and flags anomalies via reconstruction error. Post-hoc SHAP values localize the responsible microservice and metric.",
    dataset: "RS-Anomic (new open dataset, 12-service RobotShop application) — 100,464 normal and 14,112 anomalous instances across 10 injected anomaly types.",
    findings: [
      "Outperforms GDN, MAD-GAN, Kitsune, and a Transformer baseline on recall (e.g., 98.8% at 95:5 ratio vs 80.9% for GDN).",
      "Ablation confirms both GAT and LSTM components are necessary.",
      "SHAP localization achieves 10/10 accuracy for CPU/I-O/latency anomalies but fails entirely for subtle network anomalies.",
    ],
    limitations: ["Single-server testbed, not distributed/auto-scaling production infrastructure.", "SHAP is post-hoc, not GNN-native; explainability degrades for network-level anomalies."],
    relevance: "Provides a directly reusable architectural template (GAT + temporal layer + SHAP localization) for the explainability component, plus a reproducible open-dataset design pattern.",
  },
  {
    num: 7, title: "Graph Neural Networks for Anomaly Detection in Cloud Infrastructure (TAGAE)",
    ref: "Jakkaraju, A. (2025). Journal of Computer and Communications, 13(10), 102–116. DOI: 10.4236/jcc.2025.1310006.",
    objective: "Build a production-oriented GNN framework detecting node-, edge-, and distributed-level anomalies across large-scale cloud infrastructure under real-time latency constraints.",
    methodology: "Temporal-Attentive Graph Autoencoder (TAGAE): GAT-based structural encoder, GRU-based temporal graph convolution (TGCN), and anomaly-amplification layers trained with focal loss to counter severe class imbalance (0.1–2%). Logs, metrics, and traces are fused into one dynamic graph updated every 5 seconds.",
    dataset: "Azure-DIAD (2,143 microservices, 18,724 edges, 4,712 labeled anomalies) and GCP Managed Dataset v3 (12,887 container instances, 41,309 edges, 9,184 SRE-validated anomalies).",
    findings: [
      "94.2% F1 and 96.5% AUC-PR overall, with 68ms inference latency — a 63% reduction versus GraphSAGE.",
      "Maintains 89.1% F1 under 40% injected feature noise.",
      "Under concept-drift testing, AUC-PR drops only 8 points vs 15–17 points for GCN/GraphSAGE/GAT baselines.",
    ],
    limitations: ["Explainability gap: saliency maps identify only 60–70% of true root causes.", "Weak zero-day generalization; 37% F1 drop in cold-start deployment."],
    relevance: "Supplies rigorous quantitative baselines (F1, AUC-PR, latency, noise robustness) and validates that explainability remains genuinely unsolved in cloud performance analytics.",
  },
  {
    num: 8, title: "Explainable Graph Ensemble Learning for Multivariate Time Series Anomaly Detection in Cloud Microservice Architectures",
    ref: "O\u2019Shea, K., Yan, S., Yu, M., Chen, X., Mauceri, S., Dhariyal, B., Xu, L., O\u2019Connor, N., & Liu, M. (2025). IEEE Transactions on Cloud Computing. DOI: 10.1109/TCC.2025.3634737.",
    objective: "Improve interpretability of multivariate time-series anomaly detection in cloud microservices by explaining anomalies through temporal and topological structure rather than flat feature importance.",
    methodology: "Combines attention-based spatio-temporal GCNs with ensemble learning. Attention weights at selected layers are analyzed directly (\u201cante-hoc\u201d) to explain anomalous events without a separate post-hoc explainer.",
    dataset: "Two proprietary multivariate time-series datasets generated from a cloud microservice application.",
    findings: [
      "Achieves an averaged event-wise F1 score of 0.94 across the two datasets.",
      "Attention-weight visualizations give operators combined topological-and-temporal explanations for each flagged event.",
    ],
    limitations: ["Relies on proprietary, non-public datasets.", "Ensemble + attention architecture adds inference overhead."],
    relevance: "Demonstrates that GNN attention weights can serve as a built-in explanation mechanism — a concrete second design option alongside post-hoc SHAP.",
  },
  {
    num: 9, title: "SHERA: SHAP-Enhanced Resource Allocation for VM Scheduling and Efficient Cloud Computing",
    ref: "Slathia, A. S., Sharma, A., Krishna, P. B., Anand, S., Rathi, A., Joseph, L., & Gao, X. Z. (2025). IEEE Access, 13, 92816–92832. DOI: 10.1109/ACCESS.2025.3568917.",
    objective: "Apply explainable AI to cloud resource-allocation and VM-scheduling decisions to improve transparency around energy efficiency and cost, rather than targeting anomaly detection directly.",
    methodology: "Random Forest, Na\u00efve Bayes, and SVM models trained on the Google Cloud Efficiency Dataset to predict optimal VM scheduling; SHAP force plots and dependence plots interpret which features drive each prediction.",
    dataset: "Google Cloud Efficiency Dataset (CPU, memory, network traffic, power consumption).",
    findings: [
      "Random Forest is the best predictor: 96.8% accuracy, RMSE 0.16.",
      "SHAP dependence plots reveal actionable scheduling insights.",
      "Removing SHAP preserved raw performance but measurably collapsed interpretability scores.",
    ],
    limitations: ["Not GNN-based — no relational/topological modeling between VMs.", "Single-cloud, single-dataset evaluation."],
    relevance: "The clearest evidence that stripping out an XAI layer measurably reduces operational transparency, supporting the project's justification for building explainability in from the start.",
  },
  {
    num: 10, title: "Detecting Anomalies in FinTech: A Graph Neural Network and Feature Selection Perspective",
    ref: "Hoang, V. T., Dinh, N., Le, V.-T., Tran-Trung, K., Nguyen Van, B., & Meethongjan, K. (2026). Computers, Materials & Continua, 86(1), 1–40. DOI: 10.32604/cmc.2025.068733.",
    objective: "Provide a comprehensive survey of GNN-based anomaly detection specifically within FinTech and digital-banking systems, emphasizing feature selection for high-dimensional, noisy financial data.",
    methodology: "Literature synthesis covering GNN architectures (GCN, GAT, GraphSAGE, R-GCN, EvolveGCN), feature-selection families (filter, wrapper, embedded), and industry case studies (NVIDIA GNN+XGBoost pipeline, Alipay heterogeneous GNN system).",
    dataset: "Not applicable — review paper synthesizing multiple primary studies and deployed industry systems.",
    findings: [
      "Categorizes FinTech anomalies (fraud, laundering, market manipulation, insider threats, bot attacks) requiring different modeling granularities.",
      "Identifies interpretability as a principal open challenge — GNNs are frequently black boxes for regulators.",
      "Recommends XAI for GNNs, cost-sensitive learning, and temporal/dynamic GNNs as priority research directions.",
    ],
    limitations: ["No new empirical results (survey).", "Industry case studies described at a high level only."],
    relevance: "The project's strongest domain anchor — confirms GNNs as an accepted paradigm for financial fraud analytics and explainability as an unmet regulatory need in banking specifically.",
  },
];

const member3papers = [
  {
    num: 11, title: "Real-Time Financial Fraud Detection Using Adaptive Graph Neural Networks and Federated Learning",
    ref: "Da\u011f, A., Sahin, S., & Karak\u00f6se, M. (2025). International Journal of Management and Data Analytics, 5(1), 98–110.",
    objective: "Develop a real-time, privacy-preserving financial fraud detection framework that dynamically adapts to evolving fraud patterns across multiple banking institutions without exposing sensitive customer data.",
    methodology: "Integrates adaptive GNN layers with Federated Learning; local GNN parameters are aggregated globally via FL across bank nodes. Post-hoc XAI attributions are embedded into local prediction heads for regulatory-compliant decision trails.",
    dataset: "Benchmark financial transaction datasets alongside an enterprise multi-bank transactional log dataset (1.2M+ account nodes and temporal edges).",
    findings: [
      "15–30% increase in fraud detection accuracy over baseline ML models and static GNNs.",
      "Reduces false-positive rates by 28.4% across federated banking nodes.",
      "Preserves data privacy under GDPR/PCI-DSS constraints while maintaining convergence.",
    ],
    limitations: ["Communication overhead during FL aggregation increases sync latency.", "Explanations lack global topological context across the federated network."],
    relevance: "Demonstrates how GNNs pair with privacy-preserving cloud topologies (Federated Learning), establishing a baseline for distributed banking cloud architecture.",
  },
  {
    num: 12, title: "Combining Graph Neural Networks and Anomaly Detection for Low-Latency Credit Card Fraud Prevention",
    ref: "Albert, N., & Finnegan, A. (2025). International Journal of Advanced Signal and Image Processing, 12(2), 1880–1894.",
    objective: "Design a hybrid dual-component architecture detecting multi-entity fraud schemes while operating within strict real-time payment gateway latency constraints (<50ms).",
    methodology: "Two-path pipeline: a GNN pathway for structural relational patterns plus a statistical anomaly detection pathway, with dynamic weighting. Optimizations include graph pruning, asynchronous feature computation, 8-bit model quantization, and GPU acceleration.",
    dataset: "IEEE-CIS Fraud Detection dataset (~590,000 transactions, 3.5% fraud) and a proprietary bank dataset (~50 million transactions, 0.1% fraud imbalance).",
    findings: [
      "Outperforms Random Forest and XGBoost in ROC-AUC with significant false-positive reduction.",
      "Reaches sub-50ms inference latency required for live payment processing.",
      "Generates real-time interpretable explanations of influential neighbors and deviating features.",
    ],
    limitations: ["Graph pruning may drop long-tail dependencies for dormant accounts.", "Performance degrades under cold-start conditions for novel accounts."],
    relevance: "Supplies rigorous quantitative benchmarks for cloud inference latency (<50ms) and proves GNN relational modeling can be optimized for real-time payment rails.",
  },
  {
    num: 13, title: "Explainable Hybrid Graph Neural Networks and Large Language Models for Intelligent Financial Fraud Detection and Risk Analytics",
    ref: "Collins, N., Gabriel, S., Mate, Z., Micheal, J., & Michael, G. (2026). IEEE Conference Proceedings / ResearchGate.",
    objective: "Bridge the explainability gap in automated banking compliance by unifying structural GNN transaction embeddings with LLM narrative reasoning.",
    methodology: "Combines a heterogeneous GNN (R-GCN) extracting graph topology embeddings (suspicious clusters, circular transfer rings) with an LLM processing unstructured text (SARs, customer communications) to generate human-readable audit trails.",
    dataset: "Proprietary digital banking risk dataset comprising transaction graph clusters paired with unstructured compliance log narratives.",
    findings: [
      "Outperforms single-modality GNN and LLM models on complex, coordinated fraud rings.",
      "Substantially reduces manual compliance review time (45% reduction) by automating audit report generation.",
      "Identifies money laundering patterns invisible to isolated tabular or narrative analysis.",
    ],
    limitations: ["High computational footprint from LLM inference requires specialized GPU clusters.", "Best suited for asynchronous/batch auditing rather than inline authorization."],
    relevance: "Provides an architectural template for combining GNN structural outputs with XAI/LLM layers to fulfill digital banking regulatory and auditing mandates.",
  },
  {
    num: 14, title: "ECCFD-GNN: A Novel Risk-Sensitive Graph Neural Network Model for Fraudulent Transaction Detection",
    ref: "Srivastava, S., Gupta, V., Mehndiratta, V., & Rani, S. (2026). Advances in Sustainable Science Engineering and Technology, 8(3), 02603032.",
    objective: "Address extreme class imbalance in credit card transaction graphs by introducing a multi-graph structural framework and explicit risk-score integration.",
    methodology: "Constructs three graph topologies — KNN graphs, Radius Graphs (spatio-temporal proximity), and Feature-Correlation Graphs — and incorporates a dynamic risk-score feature derived from cardholder behavior directly into message-passing aggregation.",
    dataset: "Real-world credit card transaction datasets with severe class imbalance, evaluated via graph-aware cross-validation.",
    findings: [
      "Radius and Feature-Correlation graphs effectively capture subtle interdependencies traditional models miss.",
      "Achieves high precision and recall on extreme minority-class fraud instances.",
      "Ablation confirms combining feature-correlation structures with risk scoring significantly reduces misclassifications.",
    ],
    limitations: ["Constructing multiple parallel graphs increases memory consumption at scale.", "Radius threshold parameters require periodic domain tuning."],
    relevance: "Demonstrates how custom multi-graph topologies and feature-correlation structures can be engineered into GNNs to handle extreme class imbalance in digital banking.",
  },
  {
    num: 15, title: "SpaceGNN: Multi-Space Graph Neural Network for Node Anomaly Detection with Extremely Limited Labels",
    ref: "Dong, Y., et al. (2025). Proceedings of the International Conference on Learning Representations (ICLR).",
    objective: "Detect anomalous nodes in complex transaction and cloud infrastructure networks when labeled fraud data is extremely scarce (<0.1% labeled nodes).",
    methodology: "Multi-space GNN architecture projecting node relationships into both Euclidean space (local attribute similarities) and Hyperbolic space (hierarchical structures, power-law distributions), aligned via a joint loss function under minimal semi-supervised supervision.",
    dataset: "Benchmark graph anomaly datasets including financial transaction network benchmarks (Elliptic, FinGNN) and cloud topology graphs.",
    findings: [
      "Outperforms GCN, GraphSAGE, and GAT baselines by 18.2% AUC-ROC under ultra-low label availability (1–5 labeled anomalies per 10,000 nodes).",
      "Effectively captures hierarchical money-laundering trees and nested cloud infrastructure dependencies via hyperbolic embeddings.",
    ],
    limitations: ["High mathematical complexity/manifold operations increase training time per epoch.", "Requires careful tuning of hyperbolic curvature hyperparameters."],
    relevance: "Solves cold-start label scarcity in enterprise digital banking, enabling effective GNN anomaly detection before extensive labeled fraud databases accumulate.",
  },
];

function paperBlock(p) {
  const blocks = [
    H3(`[${p.num}] ${p.title}`),
    P(p.ref, { italics: true }),
    Lbl("Objective", p.objective),
    Lbl("Methodology", p.methodology),
    Lbl("Dataset", p.dataset),
    new Paragraph({ children: [new TextRun({ text: "Key Findings:", bold: true, font: FONT, size: 22 })], spacing: { after: 60 } }),
    ...p.findings.map(f => bullet(f)),
    new Paragraph({ children: [new TextRun({ text: "Limitations:", bold: true, font: FONT, size: 22 })], spacing: { before: 60, after: 60 } }),
    ...p.limitations.map(f => bullet(f)),
    Lbl("Relevance to Project", p.relevance),
  ];
  return blocks;
}

const compRows = [
  ["1", "Dou et al., 2020", "Multi-relation GNN + RL neighbor selector", "Fraud graphs (Yelp, Amazon)", "Outperforms GCN/GraphSAGE under camouflage"],
  ["2", "Liu et al., 2021", "Label-balanced sampler + neighborhood choosing", "Fraud graphs + partner bank data", "Improved AUC/F1/G-Mean under extreme imbalance"],
  ["3", "Pareja et al., 2020", "GRU/LSTM-evolved GCN weights", "Dynamic graphs (Elliptic Bitcoin)", "Generalizes to unseen nodes at inference"],
  ["4", "Xiang et al., 2023", "Gated temporal attention + risk propagation", "Industrial credit card transactions", "Strong accuracy with <10% labeled data"],
  ["5", "Zheng et al., 2019", "GCN + attention-based temporal GRU", "Dynamic interaction graphs", "Higher AUC with far fewer labeled anomalies"],
  ["6", "Akmeemana et al., 2025", "GAT + Bi-LSTM autoencoder", "Cloud microservices (RS-Anomic)", "Up to 98.8% recall; SHAP localizes 10/10"],
  ["7", "Jakkaraju, 2025", "GAT + GRU/TGCN (TAGAE)", "Cloud infra (Azure-DIAD, GCP v3)", "94.2% F1, 96.5% AUC-PR, 68ms latency"],
  ["8", "O\u2019Shea et al., 2025", "Attention spatio-temporal GCN + ensemble", "Cloud microservices (proprietary)", "0.94 averaged event-wise F1"],
  ["9", "Slathia et al., 2025", "RF/Na\u00efve Bayes/SVM (non-GNN)", "Cloud VM scheduling", "96.8% accuracy; SHAP-driven interpretability"],
  ["10", "Hoang et al., 2026", "Survey: GCN/GAT/GraphSAGE/R-GCN/EvolveGCN", "FinTech / digital banking", "Frames XAI-for-GNN as open FinTech need"],
  ["11", "Da\u011f et al., 2025", "Adaptive GNN + Federated Learning", "Federated digital banking (1.2M nodes)", "+15–30% accuracy; 28.4% false-positive drop"],
  ["12", "Albert & Finnegan, 2025", "Dual GNN (GraphSAGE/GAT) + anomaly filter", "Credit card payments (IEEE-CIS)", "Sub-50ms latency; strong ROC-AUC gain"],
  ["13", "Collins et al., 2026", "Heterogeneous GNN (R-GCN) + LLM", "Digital banking risk & SAR logs", "45% reduction in compliance review time"],
  ["14", "Srivastava et al., 2026", "ECCFD-GNN (Radius + Correlation GNN)", "Credit card transactions (extreme imbalance)", "Superior precision/recall at 0.1% fraud"],
  ["15", "Dong et al., 2025", "SpaceGNN (Euclidean + Hyperbolic)", "Financial networks & cloud graphs", "+18.2% AUC-ROC under extreme label scarcity"],
];

const gapsM1 = [
  "Adversarial robustness is rarely addressed: most GNN fraud detectors assume benign neighborhoods and do not explicitly counter camouflaged fraudsters.",
  "Class imbalance is handled ad hoc: structured, graph-aware balanced sampling outperforms naive oversampling yet remains underused in production pipelines.",
  "Static graph assumptions limit real-world deployment where new accounts and relationships are created continuously.",
  "Label scarcity in production is underexplored: fully supervised approaches assume large labeled datasets that rarely reflect real banking pipelines.",
];
const gapsM2 = [
  "No reviewed system combines GNN-based cloud performance/anomaly detection with native explainability in a digital-banking-specific deployment context; cloud-generic systems (GAL-MAD, TAGAE, O\u2019Shea et al.) are not banking-specific, while the FinTech survey is domain-specific but not cloud-performance-specific.",
  "Explainability quality is domain-dependent and uneven: SHAP and attention methods reliably explain node/resource-level anomalies but struggle with fine-grained network-level anomalies.",
  "Reproducibility is inconsistent: several reviewed systems rely on proprietary or partially disclosed datasets, complicating benchmark comparison.",
  "Regulatory-grade, auditable explainability is explicitly called out as an open need in FinTech but not yet demonstrated end-to-end in any single reviewed cloud-performance system.",
];
const gapsM3 = [
  "No single system integrates real-time sub-50ms inference, privacy-preserving multi-tenant federation, deep XAI regulatory auditing, and class-imbalance resilience into one cloud-native microservice framework.",
  "A trade-off exists between latency and explainability depth: sub-50ms systems use lightweight attributions while deep narrative XAI engines introduce overhead unsuitable for live payment gateways; a tiered pipeline remains underexplored.",
  "Cold-start and imbalance bottlenecks persist in production — novel accounts (label scarcity) and extreme class imbalance (~0.1% fraud) cause message passing to over-smooth minority fraud signals.",
];
const combinedGap = "Across all fifteen papers, no existing system unifies adversarial-camouflage robustness, structured class-imbalance handling, dynamic/temporal graph adaptation, native regulatory-grade explainability, and low-latency cloud-native deployment within a single digital banking platform. Individual papers solve one or two of these dimensions well (e.g., CARE-GNN for camouflage, PC-GNN for imbalance, EvolveGCN for dynamic graphs, TAGAE for latency, Collins et al. for LLM-based auditing) but none combine all of them into one deployable, tiered cloud architecture. This combined gap is the precise problem space the proposed project addresses.";

const novelty = [
  "Unified multi-pillar design: combines camouflage-resistant neighbor selection (CARE-GNN), balanced graph sampling (PC-GNN), dynamic weight evolution (EvolveGCN), and semi-supervised temporal attention (GTAN, AddGraph) into a single fraud-detection backbone, rather than adopting only one mechanism as most existing systems do.",
  "Tiered latency-aware architecture: separates an inline, sub-50ms GNN scoring path (informed by Albert & Finnegan) from an asynchronous deep-explainability and LLM-based compliance-auditing path (informed by Collins et al.), resolving the latency-vs-explainability-depth trade-off identified as an open gap in the literature.",
  "Regulatory-first explainability: treats explainability as a first-class design requirement from the outset (per SHERA's finding that removing XAI measurably collapses interpretability), rather than retrofitting an explainer after the fact.",
  "Cloud-native, digital-banking-specific scope: unlike cloud-generic anomaly detectors (GAL-MAD, TAGAE, O\u2019Shea et al.) or banking-specific but non-cloud-architected fraud models, the proposed system is explicitly designed as a deployable AWS microservice pipeline for digital banking.",
  "Dual robustness to both adversarial evasion and extreme imbalance simultaneously, rather than addressing either camouflage or imbalance alone as in most single-paper approaches.",
];

const awsArchText = [
  P("The proposed cloud architecture separates the system into a real-time inline scoring path and an asynchronous explainability/compliance path, connected through a shared event bus and feature/graph store. The high-level flow is as follows:"),
  bullet("Transaction events from the digital banking application are published to Amazon API Gateway, which forwards authenticated requests to an inline AWS Lambda / containerized ECS microservice performing sub-50ms GNN inference for live transaction scoring."),
  bullet("The graph feature store (account, card, merchant, and device relationships) is maintained in Amazon RDS (relational metadata) and Amazon S3 (versioned graph snapshots and training data), with SageMaker endpoints hosting the trained GNN model for inference."),
  bullet("Transactions flagged as high-risk or borderline are routed asynchronously to a compliance-auditing pipeline: an SNS topic triggers a Lambda/SageMaker worker that runs the deeper explainability layer (attention/SHAP + narrative audit-trail generation) and stores results in S3 for regulator review."),
  bullet("SageMaker is used for both model training (batch retraining and incremental weight-evolution updates) and hosting real-time and batch-transform inference endpoints."),
  bullet("CloudWatch monitors inference latency, error rates, and model drift metrics across all services, feeding alarms back into SNS for operational alerting."),
  bullet("IAM roles and policies enforce least-privilege access between microservices, the model registry, and the data stores, supporting the regulatory (GDPR/PCI-DSS-equivalent) data protection requirements identified in the literature review."),
];

const systemArchText = [
  P("At the system level, the workflow proceeds in five stages:"),
  bullet("1. Ingestion — transaction and account-relationship events stream into the platform and are used to incrementally update the live transaction graph."),
  bullet("2. Inline GNN Scoring — the camouflage-resistant, imbalance-aware GNN backbone scores each transaction against the current graph state within latency budget, returning an approve/hold/flag decision."),
  bullet("3. Dynamic Graph Update — new nodes and edges are incorporated via the weight-evolution mechanism, avoiding full model retraining as the graph grows."),
  bullet("4. Asynchronous Explainability & Audit — flagged transactions are routed to the deeper explainability/LLM-based auditing pipeline, generating regulator-facing narrative reports."),
  bullet("5. Feedback & Retraining — confirmed fraud/legitimate outcomes are fed back into the label-balanced sampler for periodic model retraining, closing the loop."),
];

function diagramPlaceholder(title, desc) {
  return new Table({
    width: { size: 9000, type: WidthType.DXA },
    columnWidths: [9000],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: 9000, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: "F2F2F2" },
      margins: { top: 200, bottom: 200, left: 200, right: 200 },
      children: [
        new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: title, bold: true, font: FONT, size: 22 })], spacing: { after: 100 } }),
        new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: desc, italics: true, font: FONT, size: 20 })] }),
      ],
    })] })],
  });
}

const datasetHeaders = ["Dataset", "Source / URL", "Size / Records", "Features", "License", "Purpose", "Preprocessing"];
const datasetRows = [
  ["Yelp Fraud (Spam Review)", "DGL / GitHub (dgl.data.FraudDataset), used in Dou et al. 2020", "~45,954 nodes, 3 relation types", "Review text embeddings, rating, user/product relations", "Research use (academic benchmark)", "Camouflage-resistant fraud detector benchmarking", "Graph construction (R-U-R, R-S-R, R-T-R relations), feature normalization"],
  ["Amazon Fraud", "DGL / GitHub (dgl.data.FraudDataset), used in Dou et al. 2020, Liu et al. 2021", "~11,944 nodes, 3 relation types", "Review/rating features, user-product-time relations", "Research use (academic benchmark)", "Imbalance-aware sampling and camouflage robustness testing", "Multi-relation graph construction, label-balanced subgraph sampling"],
  ["Elliptic Bitcoin Dataset", "Kaggle (Elliptic Data Set), used in Pareja et al. 2020, Dong et al. 2025", "203,769 nodes, 234,355 edges", "166 anonymized transaction features, licit/illicit/unknown labels", "Open (Kaggle terms)", "Dynamic graph adaptation and low-label anomaly detection benchmarking", "Temporal snapshot splitting, unknown-label masking for semi-supervised evaluation"],
  ["IEEE-CIS Fraud Detection", "Kaggle (ieee-fraud-detection competition)", "~590,000 transactions, 3.5% fraud", "Transaction amount, card, device, and identity features", "Kaggle competition license (research use)", "Low-latency inline scoring benchmark", "Missing-value imputation, categorical encoding, graph construction from shared identifiers"],
  ["Synthetic Digital Banking Transaction Graph", "Generated in-house for this project (chaos-engineering / synthetic anomaly injection, following TAGAE and AddGraph methodology)", "To be defined during implementation (target: 100K+ nodes)", "Account, card, merchant, device nodes; transaction edges with amount/time/location", "Internally generated — no external license", "Prototype the tiered inline + asynchronous architecture prior to real bank data access", "Synthetic anomaly injection, relation-type labeling, temporal snapshotting"],
];

const awsServices = [
  ["Amazon EC2", "Hosts containerized training jobs and any custom GNN inference services that require persistent, GPU-backed compute outside of managed SageMaker endpoints."],
  ["Amazon S3", "Stores raw and processed transaction data, versioned graph snapshots, trained model artifacts, and generated compliance audit reports."],
  ["AWS Lambda", "Executes lightweight, event-driven functions — inline pre/post-processing of transaction events, and asynchronous triggers for the explainability/audit pipeline."],
  ["Amazon SageMaker", "Trains the GNN models (including periodic weight-evolution retraining) and hosts real-time inference endpoints for both the fast inline scorer and the deeper explainability model."],
  ["Amazon RDS", "Stores relational metadata for accounts, cards, and merchants, and maintains structured audit-trail records for compliance queries."],
  ["Amazon API Gateway", "Exposes the transaction-scoring API to the digital banking application, handling authentication, throttling, and request routing to the inline inference service."],
  ["AWS IAM", "Enforces least-privilege access control between microservices, data stores, and the model registry, supporting GDPR/PCI-DSS-aligned data protection."],
  ["Amazon CloudWatch", "Monitors inference latency, throughput, error rates, and model-drift metrics across all services, triggering alarms for operational and model-health issues."],
  ["Amazon SNS", "Publishes flagged-transaction events from the inline scorer to the asynchronous explainability/compliance-auditing workers, and delivers CloudWatch alarm notifications to the operations team."],
];

const workDist = [
  ["Haris K", "Literature Survey — Papers 1–5 (camouflage-resistant, imbalance-aware, and dynamic-graph GNN foundations); Research Gap Analysis (Member 1 gaps); AWS Services Planning; overall document consolidation."],
  ["Keshav Gokaram", "Literature Survey — Papers 6–10 (explainable cloud-infrastructure anomaly detection); Research Gap Analysis (Member 2 gaps); Proposed AWS Cloud Architecture and diagram."],
  ["Harish Kumar", "Literature Survey — Papers 11–15 (digital banking fraud detection, federated learning, and low-latency architectures); Research Gap Analysis (Member 3 gaps); Complete System Architecture, Dataset Details, and Novelty Summary."],
];

const references = [
  "[1]  Y. Dou, Z. Liu, L. Sun, Y. Deng, H. Peng, and P. S. Yu, “Enhancing Graph Neural Network-based Fraud Detectors against Camouflaged Fraudsters,” in Proc. 29th ACM Int. Conf. Information and Knowledge Management (CIKM), 2020, pp. 315–324.",
  "[2]  Y. Liu, X. Ao, Z. Qin, J. Chi, J. Feng, H. Yang, and Q. He, “Pick and Choose: A GNN-based Imbalanced Learning Approach for Fraud Detection,” in Proc. Web Conference (WWW), 2021, pp. 3168–3177.",
  "[3]  A. Pareja, G. Domeniconi, J. Chen, T. Ma, T. Suzumura, H. Kanezashi, T. Kaler, T. Schardl, and C. Leiserson, “EvolveGCN: Evolving Graph Convolutional Networks for Dynamic Graphs,” in Proc. AAAI Conf. Artificial Intelligence, vol. 34, no. 4, 2020, pp. 5363–5370.",
  "[4]  S. Xiang, M. Zhu, D. Cheng, E. Li, R. Zhao, Y. Ouyang, L. Chen, and Y. Zheng, “Semi-Supervised Credit Card Fraud Detection via Attribute-Driven Graph Representation,” in Proc. AAAI Conf. Artificial Intelligence, vol. 37, no. 12, 2023, pp. 14557–14565.",
  "[5]  L. Zheng, Z. Li, J. Li, Z. Li, and J. Gao, “AddGraph: Anomaly Detection in Dynamic Graph via Attention-based Temporal GCN,” in Proc. 28th Int. Joint Conf. Artificial Intelligence (IJCAI), 2019, pp. 4419–4425.",
  "[6]  L. Akmeemana, H. Faiz, C. Attanayake, and S. Wickramanayake, “GAL-MAD: Towards Explainable Anomaly Detection in Microservice Applications Using Graph Attention Networks,” arXiv:2504.00058, 2025.",
  "[7]  A. Jakkaraju, “Graph Neural Networks for Anomaly Detection in Cloud Infrastructure,” Journal of Computer and Communications, vol. 13, no. 10, pp. 102–116, 2025.",
  "[8]  K. O’Shea, S. Yan, M. Yu, X. Chen, S. Mauceri, B. Dhariyal, L. Xu, N. O’Connor, and M. Liu, “Explainable Graph Ensemble Learning for Multivariate Time Series Anomaly Detection in Cloud Microservice Architectures,” IEEE Trans. Cloud Computing, 2025.",
  "[9]  A. S. Slathia, A. Sharma, P. B. Krishna, S. Anand, A. Rathi, L. Joseph, and X. Z. Gao, “SHERA: SHAP-Enhanced Resource Allocation for VM Scheduling and Efficient Cloud Computing,” IEEE Access, vol. 13, pp. 92816–92832, 2025.",
  "[10] V. T. Hoang, N. Dinh, V.-T. Le, K. Tran-Trung, B. Nguyen Van, and K. Meethongjan, “Detecting Anomalies in FinTech: A Graph Neural Network and Feature Selection Perspective,” Computers, Materials & Continua, vol. 86, no. 1, pp. 1–40, 2026.",
  "[11] A. Dağ, S. Sahin, and M. Karaköse, “Real-Time Financial Fraud Detection Using Adaptive Graph Neural Networks and Federated Learning,” International Journal of Management and Data Analytics, vol. 5, no. 1, pp. 98–110, 2025.",
  "[12] N. Albert and A. Finnegan, “Combining Graph Neural Networks and Anomaly Detection for Low-Latency Credit Card Fraud Prevention,” International Journal of Advanced Signal and Image Processing, vol. 12, no. 2, pp. 1880–1894, 2025.",
  "[13] N. Collins, S. Gabriel, Z. Mate, J. Micheal, and G. Michael, “Explainable Hybrid Graph Neural Networks and Large Language Models for Intelligent Financial Fraud Detection and Risk Analytics,” IEEE Conference Proceedings, 2026.",
  "[14] S. Srivastava, V. Gupta, V. Mehndiratta, and S. Rani, “ECCFD-GNN: A Novel Risk-Sensitive Graph Neural Network Model for Fraudulent Transaction Detection,” Advances in Sustainable Science Engineering and Technology, vol. 8, no. 3, 2026.",
  "[15] Y. Dong et al., “SpaceGNN: Multi-Space Graph Neural Network for Node Anomaly Detection with Extremely Limited Labels,” in Proceedings of the International Conference on Learning Representations (ICLR), 2025."
];

const doc = new Document({
  sections: [{
    properties: {
      page: {
        margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 },
      }
    },
    headers: {
      default: new Header({
        children: [
          new Paragraph({
            children: [new TextRun({ text: "PROJECT PHASE-I REPORT", font: FONT, size: 20 })],
            alignment: AlignmentType.RIGHT,
          }),
        ],
      }),
    },
    footers: {
      default: new Footer({
        children: [
          new Paragraph({
            alignment: AlignmentType.CENTER,
            children: [
              new TextRun({
                children: [PageNumber.CURRENT],
                font: FONT, size: 20
              })
            ]
          })
        ]
      })
    },
    children: [
      ...titlePage,
      titleInfoTable(),
      new Paragraph({ children: [new PageBreak()] }),
      
      H1("1. Abstract"),
      abstract,
      
      H1("2. Problem Statement"),
      ...problemStatement,
      
      H1("3. Objectives"),
      ...objectives.map(o => bullet(o)),
      
      H1("4. Literature Survey"),
      H2("Member 1: Haris K (Papers 1–5)"),
      ...member1papers.flatMap(p => paperBlock(p)),
      H2("Member 2: Keshav Gokaram (Papers 6–10)"),
      ...member2papers.flatMap(p => paperBlock(p)),
      H2("Member 3: Harish Kumar (Papers 11–15)"),
      ...member3papers.flatMap(p => paperBlock(p)),
      
      new Paragraph({ children: [new PageBreak()] }),
      H1("5. Research Gap Analysis"),
      H2("Member 1: Haris K"),
      ...gapsM1.map(g => bullet(g)),
      H2("Member 2: Keshav Gokaram"),
      ...gapsM2.map(g => bullet(g)),
      H2("Member 3: Harish Kumar"),
      ...gapsM3.map(g => bullet(g)),
      H2("Combined Gap Identified"),
      P(combinedGap),
      
      H1("6. Novelty of the Proposed Solution"),
      ...novelty.map(n => bullet(n)),
      
      H1("7. Proposed Cloud Architecture"),
      ...awsArchText,
      diagramPlaceholder("AWS Cloud Architecture Diagram Placeholder", "(Insert AWS_Architecture.png here)"),
      ...systemArchText,
      diagramPlaceholder("System Data Flow Architecture Placeholder", "(Insert System_Architecture.png here)"),
      
      new Paragraph({ children: [new PageBreak()] }),
      H1("8. Dataset Details"),
      simpleTable(datasetHeaders, datasetRows, [1500, 1500, 1000, 1500, 1000, 1500, 1000]),
      
      H1("9. AWS Services Planning"),
      simpleTable(["AWS Service", "Proposed Use Case"], awsServices, [2000, 7000]),
      
      H1("10. Work Distribution"),
      simpleTable(["Team Member", "Assigned Responsibilities"], workDist, [2000, 7000]),
      
      new Paragraph({ children: [new PageBreak()] }),
      H1("11. References"),
      ...references.map(r => refPara(r))
    ],
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("../docs/Project_Phase_I_Report.docx", buffer);
  console.log("Document created successfully at ../docs/Project_Phase_I_Report.docx");
});
