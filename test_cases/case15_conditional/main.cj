// 测试用例15: 条件分支中的竞争
// 在条件分支中访问共享变量

main() {
    var flag: Bool = true
    var counter: Int64 = 0
    
    // 线程1: 条件写
    spawn {
        if flag {
            counter = counter + 1  // 条件写操作
        }
    }
    
    // 线程2: 条件读
    spawn {
        if flag {
            let value = counter  // 条件读操作，可能存在竞争
            println(value)
        }
    }
    
    println(counter)
}