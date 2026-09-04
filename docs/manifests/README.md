# Zip checksums

Zips used for integration testing. Release assets on [datasets-v0.1](https://github.com/finnjclancy/cnd-mne-converter/releases/tag/datasets-v0.1), not git.

| Dataset | Asset | Size (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| AliceSpeech | `AliceSpeech.zip` | 1,133,117,185 | `70beaca7cf4e6d92b847c5213041566286da41ccd2d55b6703def7a604a718a5` |
| AAD KULeuven | `AAD_KULeuven.zip` | 1,416,416,404 | `18956b3e84c96e4edbc428dbd0613c33013f1956afde83c890213e0f6b987339` |
| Music Imagery | `datasetCND_musicImagery.zip` | 1,650,738,023 | `317c0b9a19f5804a0b69eb67a05d9e9856a21a39fde03261262f3716550a4ebe` |
| Lalor Natural Speech, part 1 | `datasetCND_LalorNatSpeech.zip.part-aa` | 1,992,294,400 | `e4de0bbbf6f784215451fa33f605a278d8df85d050053d0f58a1189406d7e6cb` |
| Lalor Natural Speech, part 2 | `datasetCND_LalorNatSpeech.zip.part-ab` | 1,526,633,322 | `9f8fb4a8d3e929071ae5bdb8247b9cfa773bb5372be7b248f943cd9b5cdd1131` |

Complete Lalor zip: 3,518,927,722 bytes, SHA-256 `4626367ba97f35b5a9e9e15ff19cbe57384a264d56bd076e81b322cbcf725bff`.

## Licence and citation

These are dataset mirrors, not part of this repo's BSD licence. Keep each archive under its original terms and cite both the dataset and [CNSP](https://cnsp-resources.readthedocs.io/en/latest/citation.html).

- **Lalor Natural Speech:** the [underlying data](https://doi.org/10.5061/dryad.070jc) are [CC0](https://creativecommons.org/publicdomain/zero/1.0/). Cite Broderick et al. (2018), DOI [`10.1016/j.cub.2018.01.080`](https://doi.org/10.1016/j.cub.2018.01.080). CNSP does not state a separate licence for its converted CND archive, so continued mirroring should be confirmed with the lab.
- **AliceSpeech:** [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite Brennan, *EEG Datasets for Naturalistic Listening to “Alice in Wonderland”*, DOI [`10.7302/Z29C6VNH`](https://doi.org/10.7302/Z29C6VNH), and Brennan & Hale (2019). This asset is CNSP's CND conversion, mirrored here without further changes.
- **AAD KULeuven:** [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/). Cite Das, Francart, and Bertrand's [Zenodo record](https://doi.org/10.5281/zenodo.4004271) and Biesmans et al. (2016), DOI [`10.1109/TNSRE.2016.2571900`](https://doi.org/10.1109/TNSRE.2016.2571900). This asset is CNSP's CND conversion, mirrored here without further changes. Redistribution must remain non-commercial, attributed, and under the same licence.
- **Music Imagery:** the underlying [Dryad data](https://doi.org/10.5061/dryad.dbrv15f0j) are CC0; the CND archive includes its own BSD 3-Clause notice. Cite Marion, Di Liberto, and Shamma (2021), parts [I](https://doi.org/10.1523/JNEUROSCI.0183-21.2021) and [II](https://doi.org/10.1523/JNEUROSCI.0184-21.2021).

The CNSP site says each dataset keeps its original licence. Its BSD licence covers CNSP software and documentation; it does not replace these dataset terms.

Downloaded from CNSP, not on that release:

| Dataset | Archive | Size (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| Lalor Reversed Speech | `datasetCND_LalorNatSpeechReverse.zip` | 2,026,330,837 | `c0514445a959249a8869648909d3b513b41415d8d70a18dc5910cfb569ea6c56` |
| SparrKULee2 | `SparrKULee2.zip` | 5,728,958,354 | `a9baec9634e610c221da509078e034a7f6fe91d6903fb7f253c11eae8a278519` |

Glue Lalor:

```bash
cat datasetCND_LalorNatSpeech.zip.part-aa \
    datasetCND_LalorNatSpeech.zip.part-ab \
    > datasetCND_LalorNatSpeech.zip
shasum -a 256 datasetCND_LalorNatSpeech.zip
```

Unmodified public archives; Lalor is split byte-for-byte into two release assets. CNSP remains the source for the CND copies.
