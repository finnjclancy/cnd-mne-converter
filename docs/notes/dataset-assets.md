# Public CND test datasets

The public datasets used for integration testing are attached to the private
GitHub release [datasets-v0.1](https://github.com/finnjclancy/cnd-mne-converter/releases/tag/datasets-v0.1).
They are release assets rather than Git-tracked files so that normal clones of
the source repository remain small.

## Assets

| Dataset | Release asset | Size (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| AliceSpeech | `AliceSpeech.zip` | 1,133,117,185 | `70beaca7cf4e6d92b847c5213041566286da41ccd2d55b6703def7a604a718a5` |
| AAD KULeuven | `AAD_KULeuven.zip` | 1,416,416,404 | `18956b3e84c96e4edbc428dbd0613c33013f1956afde83c890213e0f6b987339` |
| Music Imagery | `datasetCND_musicImagery.zip` | 1,650,738,023 | `317c0b9a19f5804a0b69eb67a05d9e9856a21a39fde03261262f3716550a4ebe` |
| Lalor Natural Speech, part 1 | `datasetCND_LalorNatSpeech.zip.part-aa` | 1,992,294,400 | `e4de0bbbf6f784215451fa33f605a278d8df85d050053d0f58a1189406d7e6cb` |
| Lalor Natural Speech, part 2 | `datasetCND_LalorNatSpeech.zip.part-ab` | 1,526,633,322 | `9f8fb4a8d3e929071ae5bdb8247b9cfa773bb5372be7b248f943cd9b5cdd1131` |

The complete Lalor ZIP is 3,518,927,722 bytes and has SHA-256
`4626367ba97f35b5a9e9e15ff19cbe57384a264d56bd076e81b322cbcf725bff`.

## Additional authoritative archives tested

These larger archives were downloaded from CNSP and checksum-verified locally.
They are referenced directly rather than duplicated in the GitHub release.

| Dataset | Official archive | Size (bytes) | SHA-256 |
| --- | --- | ---: | --- |
| Lalor Reversed Speech | `datasetCND_LalorNatSpeechReverse.zip` | 2,026,330,837 | `c0514445a959249a8869648909d3b513b41415d8d70a18dc5910cfb569ea6c56` |
| SparrKULee2 | `SparrKULee2.zip` | 5,728,958,354 | `a9baec9634e610c221da509078e034a7f6fe91d6903fb7f253c11eae8a278519` |

## Reconstruct Lalor Natural Speech

On macOS or Linux:

```bash
cat datasetCND_LalorNatSpeech.zip.part-aa \
    datasetCND_LalorNatSpeech.zip.part-ab \
    > datasetCND_LalorNatSpeech.zip
shasum -a 256 datasetCND_LalorNatSpeech.zip
unzip -t datasetCND_LalorNatSpeech.zip
```

On PowerShell:

```powershell
$parts = @(
  "datasetCND_LalorNatSpeech.zip.part-aa",
  "datasetCND_LalorNatSpeech.zip.part-ab"
)
$out = [System.IO.File]::Create("datasetCND_LalorNatSpeech.zip")
foreach ($part in $parts) {
  $bytes = [System.IO.File]::ReadAllBytes($part)
  $out.Write($bytes, 0, $bytes.Length)
}
$out.Dispose()
Get-FileHash datasetCND_LalorNatSpeech.zip -Algorithm SHA256
```

## Provenance

These files are unmodified copies of the public archives, except that the
Lalor archive is split byte-for-byte into two release assets:

- [Lalor Natural Speech](https://www.data.cnspworkshop.net/data/datasetCND_LalorNatSpeech.zip)
- [AliceSpeech](https://www.data.cnspworkshop.net/data/AliceSpeech.zip)
- [AAD KULeuven](https://www.data.cnspworkshop.net/data/AAD_KULeuven.zip)
- [Music Imagery](https://www.data.cnspworkshop.net/data/datasetCND_musicImagery.zip)
- [Lalor Reversed Speech](https://www.data.cnspworkshop.net/data/datasetCND_LalorNatSpeechReverse.zip)
- [SparrKULee2](https://www.data.cnspworkshop.net/data/SparrKULee2.zip)

The original authors' licences, citation requirements, and dataset terms still
apply. These mirrors are for reproducible converter development and testing;
the official CNSP copies remain the authoritative sources.
