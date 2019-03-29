package main

import (
  "os"
  "bufio"
  "fmt"
  "log"
  "io"
  // "io/ioutil"
  "strings"
  "strconv"
  "encoding/json"
  "compress/gzip"
  "sync"
)

type chrompos struct {
  chrom string
  pos string
}

type sample struct {
  sampleName string
  sampleData string
}

func makeOutput() map[chrompos][]sample {
  out := make(map[chrompos][]sample)
  return out
}

func getInputPaths() []string {
  name := fmt.Sprintf("input/%v", os.Args[1])
  infile, err := os.Open(name)
  if err != nil {
    log.Fatal(err)
  }
  r := bufio.NewReader(infile) // instantiate reader for file
  var out []string
  for {
    line, err := r.ReadString('\n') // read in line by line
    // fmt.Printf("%#v\n", line)
    if err == io.EOF {
      break
    }
    line = strings.Trim(line, " \n\r\t")
    out = append(out, line)
  }
  // fmt.Printf("%#v\n", out)
  return out
}

func main() {
  files := getInputPaths()
  prefList := getPreferredList() // get array of preferred chrompos pairs
  // fmt.Printf("Here is preferred list: %v\n", prefList)
  // masterOut := processFiles(files, prefList) // main processing pipeline
  masterOut := parallelProcessFiles(files, prefList) // same as processFiles but processes files concurrently
  writeMaster(masterOut)
  writeTSV(masterOut, "unfiltered.tsv")
  filteredOut := filterOut(masterOut)
  writeFiltered(filteredOut)
  writeTSV(filteredOut, "filtered.tsv")
}

func filterOut(masterOut map[chrompos][]sample) map[chrompos][]sample {
  filteredOut := makeOutput()
  var keep bool
  var data string
  for key, val := range masterOut {
    keep = false
    for _, cp := range val {
      data = cp.sampleData
      if nonZero(data) {
        keep = true
        break
      }
    }
    if keep {
      filteredOut[key] = val
    }
  }
  return filteredOut
}

func nonZero(data string) bool {
  tmpString := strings.Split(data, "-")[0]
  tmpList := strings.Split(tmpString, "/")
  num, err := strconv.Atoi(tmpList[0])
  if err != nil {
    log.Fatal(err)
  }
  den, err := strconv.Atoi(tmpList[1])
  if err != nil {
    log.Fatal(err)
  }
  if num == 0 && den == 0 {
    return false
  }
  return true
}

func writeMaster(masterOut map[chrompos][]sample) {
  // fmt.Printf("\nmasterOut: %v\n", masterOut)
  temp := convertOut(masterOut)
  jout, err := json.MarshalIndent(temp, "", "  ")
  if err != nil {
    log.Fatal(err)
  }
  f, err := os.Create("unfiltered.json")
  if err != nil {
    log.Fatal(err)
  }
  defer f.Close()
  f.Write(jout)
}

func writeFiltered(filteredOut map[chrompos][]sample) {
  // fmt.Printf("\nfilteredOut: %v\n", filteredOut)
  temp := convertOut(filteredOut)
  jout, err := json.MarshalIndent(temp, "", "  ")
  if err != nil {
    log.Fatal(err)
  }
  f, err := os.Create("filtered.json")
  if err != nil {
    log.Fatal(err)
  }
  defer f.Close()
  f.Write(jout)
}

func convertOut(out map[chrompos][]sample) map[string]map[string]string {
	jout := make(map[string]map[string]string)
	for key, val := range out {
		k := fmt.Sprintf("%v-%v", key.chrom, key.pos)
		v := make(map[string]string)
		for _, obj := range val {
			v[obj.sampleName] = obj.sampleData
		}
		jout[k] = v
	}
	return jout
}

func writeTSV(out map[chrompos][]sample, fname string) {
  f, err := os.Create(fname)
  if err != nil {
    log.Fatal(err)
    return
  }
  defer f.Close()
  w := bufio.NewWriter(f)
  sampleNames := make(map[string]string)
  for _, val := range out {
    for _, obj := range val {
      sampleNames[obj.sampleName] = ""
    }
  }
  w.WriteString("chrompos.")
  i := 0
  snames := make([]string, len(sampleNames))
  for samName, _ := range sampleNames {
    snames[i] = samName
    w.WriteString("\t")
    w.WriteString(samName)
    i ++
  }
  w.WriteString("\n")
  for key, val := range out {
    k := fmt.Sprintf("%v-%v", key.chrom, key.pos)
    v := make(map[string]string)
    for _, obj := range val {
    	v[obj.sampleName] = obj.sampleData
    }
    w.WriteString(k)
    for _, samName := range snames {
      w.WriteString("\t")
      w.WriteString(v[samName])
    }
    w.WriteString("\n")
  }
  w.Flush()
}

// loads in file which contains preferred list of chrompos
// extracts chrompos pairs
// returns array of preferred chrompos pairs
func getPreferredList() []chrompos {
  var out []chrompos
  path := fmt.Sprintf("input/%v", os.Args[2])
  infile, err := os.Open(path)
  if err != nil {
    log.Fatal(err)
  }
  r := bufio.NewReader(infile) // instantiate reader for file
  for {
    rec, err := r.ReadString('\n')
    if err == io.EOF {
      break
    }
    recItems := strings.Split(rec, ":") // split line into array
    c := strings.Trim(recItems[0], " \n\t\r")
    p := strings.Trim(recItems[1], " \n\t\r")
    pref := chrompos{chrom: c, pos: p} // extract chrom and pos
    out = append(out, pref) // append to output preferred list
  }
  // fmt.Printf("%#v", out)
  return out
}

// checks if given chrompos pair is in preferred list
func isPreferred(pos chrompos, prefList []chrompos) bool {
  for _, pref := range prefList {
    if pos == pref {
      return true
    }
  }
  return false
}

func parallelProcessFiles(paths []string, prefList []chrompos) map[chrompos][]sample {
  masterOut := makeOutput()

  var wg sync.WaitGroup

  for _, path := range paths {
    wg.Add(1) // increment WaitGroup counter
    // launch goroutine to process one file
    go func(path string) {
      defer wg.Done()  // decrement the counter when the goroutine completes
      infile, err := os.Open(path)
      defer infile.Close()
      if err != nil {
        log.Fatal(err)
      }
      processFile(infile, prefList, masterOut)
    }(path)
  }
  wg.Wait() // wait for all files to finish processing
  return masterOut
}

/*
func processFiles(paths []string, prefList []chrompos) map[chrompos][]sample {
  masterOut := makeOutput()

  for _, path := range paths {
    infile, err := os.Open(path)
    if err != nil {
      log.Fatal(err)
    }
    processFile(infile, prefList, masterOut)
  }
  return masterOut
}
*/

func processFile(infile *os.File, prefList []chrompos, masterOut map[chrompos][]sample) {
  r := bufio.NewReader(infile) // instantiate reader for file
  zr, err := gzip.NewReader(r)
  if err != nil {
      fmt.Println(err)
  }

  r = bufio.NewReader(zr)

  samName := ""
  // could possibly try to run this in parallel also?? maybe not
  for {
    line, err := r.ReadString('\n') // read in line by line
    if err == io.EOF {
      break
    }
    rec := strings.Split(line, "\t") // split line to get array corresponding to record
    if len(rec) < 2 {
        continue
    }
    /*
    fmt.Printf("---%v---\n", len(rec))
    for _, val := range rec {
      fmt.Printf("%v\t", val)
    }
    */
    if rec[0] == "#CHROM" && samName == "" {
      samName = strings.Trim(rec[9], " \n\t\r\"")
    }
    pos := chrompos{chrom: rec[0], pos: rec[1]}
    // fmt.Printf("pos: %v\n", pos)
    pref := isPreferred(pos, prefList)
    if pref {
      // fmt.Printf("found a match! %v\n", pos)
      data := getData(rec)
      sam := sample{sampleName: samName, sampleData: data}
      inMaster := isInMaster(pos, masterOut)
      switch {
      case inMaster:
        masterOut[pos] = append(masterOut[pos], sam)
      default:
        // fmt.Printf("Case default\n")
        masterOut[pos] = []sample{sam}
      }
    }
  }
}

func isInMaster(pos chrompos, masterOut map[chrompos][]sample) bool {
  // fmt.Printf("Running isInMaster\n")
  for pref := range masterOut {
    if pos == pref {
      return true
    }
  }
  return false
}

func getData(rec []string) string {
  // fmt.Printf("Running getData\n")
  refAltList := getRefAltList(rec)
  ratio := getRatio(rec)
  data := buildData(refAltList, ratio)
  return data
}

func buildData(refAltList []string, ratio string) string {
  // fmt.Printf("Running buildData\n")
  // fmt.Printf("ral: %v, ratio: %v\n", refAltList, ratio)
  tmp := strings.Split(ratio, "/")
  num, err := strconv.Atoi(tmp[0])
  if err != nil {
    log.Fatal(err)
  }
  den, err := strconv.Atoi(tmp[1])
  if err != nil {
    log.Fatal(err)
  }
  data := fmt.Sprintf("%v-%v/%v", ratio, refAltList[num], refAltList[den])
  return data
}

func getRatio(rec []string) string {
  // fmt.Printf("Running getRatio\n")
  /*
  for i, v := range rec {
    fmt.Printf("%v, %v\n", i, v)
  }
  */
  tmpString := strings.Trim(rec[9],"\"")
  // fmt.Printf("%v\v", tmpString)
  tmpList := strings.Split(tmpString, ":")
  out := tmpList[0]
  return out
}

func getRefAltList(rec []string) []string {
  // fmt.Printf("Running getRefAltList\n")
  var refAltList []string
  ref := strings.Trim(rec[3], "\"")
  refAltList = append(refAltList, ref)
  altList := getAltList(strings.Trim(rec[4], "\""))
  refAltList = append(refAltList, altList...)
  return refAltList
}

func getAltList(s string) []string {
  // fmt.Printf("Running getAltList\n")
  var out []string
  tmp := strings.Split(s, ",")
  if len(tmp) == 1 {
    return out
  }
  // take all but the last value
  for i, val := range tmp {
    if i < len(tmp) - 1 {
      item := strings.Trim(val,"\" ")
      out = append(out, item)
    }
  }
  return out
}
