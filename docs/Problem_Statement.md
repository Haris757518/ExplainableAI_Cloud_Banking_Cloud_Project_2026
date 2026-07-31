# Problem Statement

Digital banking fraud detection faces four compounding challenges that existing systems address only in isolation. 

First, fraudsters actively camouflage their behavior to mimic legitimate transaction patterns, evading detectors that assume benign neighborhoods in the transaction graph. 
Second, fraudulent transactions represent a tiny minority of overall traffic (often below 1%), causing standard learning algorithms to bias toward the majority legitimate class. 
Third, digital banking graphs are inherently dynamic — new accounts, cards, and merchant relationships are created continuously, and static graph models become stale without costly full retraining. 
Fourth, regulatory frameworks (RBI guidelines, PCI-DSS, GDPR-equivalent norms) require that any automated fraud or risk decision be explainable to compliance officers and auditors, yet most high-performing GNN fraud detectors operate as opaque black boxes.

There is currently no unified, cloud-deployable system that simultaneously resolves adversarial camouflage, class imbalance, temporal graph evolution, and regulatory-grade explainability within a single low-latency architecture suitable for live digital banking transaction pipelines. This project addresses that gap by proposing an explainable, cloud-native GNN-based fraud detection and cloud performance analytics platform for digital banking.
